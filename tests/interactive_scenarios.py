"""Fixed repository-authored programs for real interactive API acceptance."""
import json
import time
from pathlib import Path

from workflow import request
from judge_protocol import wait_for

ROOT = Path(__file__).resolve().parents[1]
ACTIVE = {"compiling", "running", "stopping"}
HELLO = '#include <iostream>\nint main(){std::cout<<"Hello World\\n";}'
SINGLE = '#include <iostream>\nint main(){int a;if(std::cin>>a)std::cout<<a*2<<"\\n";}'
MULTI = '#include <iostream>\nint main(){int a,b;std::cout<<"first:"<<std::flush;std::cin>>a;std::cout<<"second:"<<a<<"\\n"<<std::flush;std::cin>>b;std::cerr<<"done\\n";std::cout<<a+b<<"\\n";}'
LINE = '#include <iostream>\n#include <string>\nint main(){std::string s;std::getline(std::cin,s);std::cout<<"["<<s<<"]\\n";}'
SCANF = '#include <cstdio>\nint main(){int x,y;if(std::scanf("%d%d",&x,&y)==2)std::printf("%d\\n",x*y);}'
BAD = '#include <iostream>\nint main(){std::cout<<1}'
ERROR = 'int main(){return 7;}'
LOOP = 'int main(){for(;;){}}'
EOF_CODE = '#include <iostream>\nint main(){int n,sum=0;while(std::cin>>n)sum+=n;std::cout<<sum<<"\\n";}'
OUTPUT_CODE = '#include <iostream>\n#include <string>\nint main(){std::cout<<std::string(18000,\'x\');}'
FIXED = [HELLO,SINGLE,MULTI,LINE,SCANF,BAD,ERROR,LOOP,EOF_CODE,OUTPUT_CODE]

def exercise_sources():
    notebook = json.loads((ROOT / "examples/CS2310_Score_Analysis.ipynb").read_text())
    references = json.loads((ROOT / "examples/score_analysis_references.json").read_text())
    title = "Debug the accumulation loop"
    reference = references[title]
    cell = notebook["cells"][reference["cell"]-1]
    src = "".join(cell["source"]).strip().removeprefix("%%cpp\n").strip()
    correct = reference["referenceSource"].strip()
    assert "n - 1" in src and "n - 1" not in correct
    return src, correct

def check(base, *, native=False, idle_limit=8):
    starter, correct = exercise_sources()
    _, room = request(base, "/api/rooms", {"name": "Interactive acceptance"})
    root = "/api/rooms/" + room["id"]
    teacher = {"X-Teacher-Key": room["teacherKey"]}
    _, task = request(base, root + "/tasks", {"title": "Accumulation", "description": "",
        "starterCode": starter, "testCases": [
            {"name":"Public","input":"5\n10 20 30 40 50\n","expectedOutput":"150\n","visibility":"public"},
            {"name":"Private","input":"3\n1 2 3\n","expectedOutput":"6\n","visibility":"hidden"}]}, **teacher)
    task_id = task["id"]
    def join(name):
        status, s = request(base, root + "/students", {"name":name})
        assert status == 201
        return {"X-Student-Key":s["studentKey"]}
    a,b = join("One"),join("Two")
    def action(headers, name, sid=None, **fields):
        data = {"taskId":task_id,"action":name,**fields}
        if sid is not None:
            data["sessionId"] = sid
        status, result = request(base, root+"/run-session", data, **headers)
        assert status == 200, (status,result)
        return result
    def start(code, who=a):
        result = action(who,"start",code=code)
        assert "sessionId" in result, result
        return result["sessionId"]
    def poll(sid, who=a):
        return action(who,"poll",sid)
    def until(sid, predicate, who=a, timeout=35):
        return wait_for(lambda:poll(sid,who),predicate,timeout=timeout)
    def running(sid, who=a):
        state = until(sid, lambda s:s["status"]!="compiling",who)
        assert state["status"]=="running" and state["stdinOpen"],state
        return state
    def send(sid, value, who=a):
        result=action(who,"input",sid,input=value)
        assert result["status"] in ACTIVE, result
    def finish(sid, who=a):
        return until(sid,lambda s:s["status"] not in ACTIVE,who,timeout=35)
    def successful(sid, expected, who=a):
        result=finish(sid,who)
        assert (result["status"],result["stdout"],result["exitCode"])==("success",expected,0),result
        return result

    assert request(base,root+"/task",**a)[1]["interactiveAvailable"] is True
    successful(start(HELLO),"Hello World\n")
    sid=start(SINGLE);running(sid);send(sid,"7\n");successful(sid,"14\n")
    sid=start(MULTI);running(sid)
    until(sid,lambda s:s["stdout"]=="first:")
    send(sid,"11\n")
    until(sid,lambda s:s["stdout"]=="first:second:11\n")
    # Still the same session, not a second compilation or a restart.
    assert poll(sid)["sessionId"]==sid and poll(sid)["status"]=="running"
    send(sid,"31\n")
    assert successful(sid,"first:second:11\n42\n")["stderr"]=="done\n"
    sid=start(MULTI);running(sid);send(sid,"11 31\n");successful(sid,"first:second:11\n42\n")
    sid=start(LINE);running(sid);send(sid,"hello two words\n");successful(sid,"[hello two words]\n")
    sid=start(SCANF);running(sid);send(sid,"4 5\n");successful(sid,"20\n")

    # Original notebook bug: entering only n must NOT deliver EOF.
    sid=start(starter);running(sid);send(sid,"5\n")
    time.sleep(3.2)
    state=poll(sid)
    assert state["status"]=="running" and state["stdinOpen"] and not state["stdout"],state
    send(sid,"10 20\n");send(sid,"30 40\n");successful(sid,"100\n")
    sid=start(starter);running(sid);send(sid,"5\n10 20 30 40 50\n");successful(sid,"100\n")
    sid=start(correct);running(sid);send(sid,"5\n10 20 30 40 50\n");successful(sid,"150\n")
    print("Accumulation: after 5 still running >3s; stepped 100; full input 100/150.",flush=True)

    result=finish(start(BAD));assert result["status"]=="compilation_error" and "error:" in result["diagnostic"],result
    result=finish(start(ERROR));assert result["status"]=="runtime_error" and result["exitCode"]==7,result
    result=finish(start(LOOP));assert result["status"]=="time_limit",result
    sid=start(EOF_CODE);running(sid);send(sid,"10 20\n")
    action(a,"eof",sid);successful(sid,"30\n")
    sid=start(SINGLE);running(sid)
    action(a,"stop",sid);assert finish(sid)["status"]=="stopped"
    sid=start(SINGLE);running(sid);result=finish(sid);assert result["status"]=="idle_timeout",result
    result=finish(start(OUTPUT_CODE));assert result["status"]=="resource_limit" and len(result["stdout"].encode())<=16384,result

    x=start(SINGLE,a);y=start(SINGLE,b);running(x,a);running(y,b)
    assert action(b,"poll",x)["status"]=="not_found"
    assert action(b,"input",x,input="999\n")["status"]=="not_found"
    assert action(a,"start",code=SINGLE)["status"]=="busy"
    send(x,"9\n",a);send(y,"15\n",b)
    successful(x,"18\n",a);successful(y,"30\n",b)
    status,_=request(base,root+"/run-session",{"action":"poll","taskId":task_id,"sessionId":x})
    assert status==403,status
    if native:
        result=finish(start(HELLO+"\n// unapproved"))
        assert result["status"]=="source_not_approved" and not result["stdout"],result
    # No free Run is a submission; submit still uses actual batch grading.
    assert request(base,root+"/progress",**teacher)[1]["attempts"]==0
    for who,code,expected in [(a,starter,"wrong_answer"),(b,correct,"accepted")]:
        status,result=request(base,root+"/submissions",{"taskId":task_id,"code":code},**who)
        assert status==201,result
        state=wait_for(lambda:request(base,root+"/task",**who)[1],
            lambda s:s["latestResult"] and s["latestResult"]["status"]==expected,timeout=105)
        assert "Private" not in json.dumps(state),state
    progress=request(base,root+"/progress",**teacher)[1]
    assert (progress["submitted"],progress["accepted"],progress["failed"])==(2,1,1),progress
    print("Real execution: hello, cin, repeated cin, grouped input, getline, scanf, prompt/stdout/stderr, EOF, stop, idle/CPU/output limits, independent sessions, authorization, batch Submit.",flush=True)
