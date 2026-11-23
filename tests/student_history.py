"""Student history stays scoped to the authenticated student and current task."""
import json
import tempfile
import unittest
from pathlib import Path

from workflow import request, server


class StudentHistory(unittest.TestCase):
    def test_current_task_own_recent_attempts(self):
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory) / "history.json"
            with server(data) as base:
                _, room = request(base, "/api/rooms", {"name": "History"})
                path = "/api/rooms/" + room["id"]
                teacher = {"X-Teacher-Key": room["teacherKey"]}
                _, record = request(base, path + "/students", {"name": "Student A"})
                first = {"X-Student-Key": record["studentKey"]}
                _, record = request(base, path + "/students", {"name": "Student B"})
                other = {"X-Student-Key": record["studentKey"]}
                self.assertEqual(request(base, path + "/task", **first)[1]["submissionHistory"], [])
                _, task = request(base, path + "/tasks",
                    {"title": "Practice", "description": "First task", "starterCode": ""}, **teacher)
                self.assertEqual(request(base, path + "/task")[0], 403)
                for index in range(52):
                    status, _ = request(base, path + "/submissions",
                        {"taskId": task["id"], "code": f"PRIVATE_SOURCE_{index}"}, **first)
                    self.assertEqual(status, 201)
                self.assertEqual(request(base, path + "/task", **other)[1]["submissionHistory"], [])
                self.assertEqual(len(request(base, path + "/task", **first)[1]["submissionHistory"]), 50)

            rooms = json.loads(data.read_text())
            attempts = rooms[room["id"]]["students"][first["X-Student-Key"]]["submissions"]
            for index, entry in enumerate(attempts):
                entry["receivedAt"] = 1700000000 + index
            attempts[-1]["judgement"] = {"status": "accepted", "passed": 2, "total": 2,
                                        "cases": [{"testId": "1", "actualOutput": "PRIVATE_FIXTURE"}]}
            data.write_text(json.dumps(rooms))

            with server(data) as base:
                own = request(base, path + "/task", **first)[1]["submissionHistory"]
                self.assertEqual([entry["receivedAt"] for entry in own], list(range(1700000051, 1700000001, -1)))
                self.assertEqual(own[0], {"receivedAt": 1700000051, "status": "accepted", "passed": 2, "total": 2})
                self.assertNotIn("PRIVATE_", json.dumps(own))
                _, next_task = request(base, path + "/tasks",
                    {"title": "New", "description": "Second task", "starterCode": ""}, **teacher)
                now = request(base, path + "/task", **first)[1]
                self.assertEqual(now["task"]["id"], next_task["id"])
                self.assertEqual(now["submissionHistory"], [])


if __name__ == "__main__":
    unittest.main()
