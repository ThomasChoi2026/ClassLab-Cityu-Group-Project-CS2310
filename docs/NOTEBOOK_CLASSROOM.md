# Notebook Classroom Integration

## Download the sample

Open the [sample Notebook on GitHub](../examples/CS2310_Score_Analysis.ipynb) and choose **Download raw file**. You can download it before starting ClassLab. The same file imports in Normal Mode and Demo Mode. A new exercise you author can be published in either mode. Actual execution and grading require an accepted Judge in Normal Mode. Demo plays only its supplied fixtures.

## Mark your own exercise

In a normal Jupyter Notebook v4 **Code** cell, put a single C++ comment on the first nonblank line:

```cpp
// @classlab exercise: Fix the grade boundary
#include <iostream>
int main() {
    int score;
    std::cin >> score;
    std::cout << (score > 60 ? "PASS" : "FAIL") << '\n';
}
```

Use the exact lowercase marker:

| First nonblank line in a C++ Code cell | What ClassLab loads |
| --- | --- |
| `// @classlab exercise: Fix the grade boundary` | A marked exercise titled “Fix the grade boundary”. |
| `// @classlab exercise` | A marked exercise using the optional Cell Metadata title or the default `ClassLab Exercise · Cell N`. |
| `// @classlab exercise;` or `// Web Class: Fix the grade boundary` | An ordinary cell if no ClassLab Metadata is present. These spellings are unrecognized. |

Use a colon (`:`) only when followed by a title. The marker is a comment and takes no semicolon. Keep normal C++ semicolons in the program below it. If your Notebook kernel uses a bare `%%cpp` first, put the marker on the next nonblank line. Markdown cells, later comments and string literals cannot mark an exercise.

Include the C++ source below the marker and save the Notebook as `.ipynb`. The importer checks the format and reports unsupported cells. Code fragments can be recognized with a warning when no `main()` is apparent. Convert `%%hermes`, `%%cpp` with arguments, Python and other Notebook commands manually before importing them as C++.

## Import, check and publish

1. Open **课前备课**; the file selector is directly visible. Upload a local .ipynb file (up to 2 MiB). The file is read only in the teacher browser, not rewritten or sent to the server.
2. The filename, original total cell count, recognized exercise count and invalid-metadata count appear. Marked exercises are the initial filter when present; otherwise All is selected. The preview opens without loading or publishing.
3. Click an exercise to load its title, description, starter, tests and pitfalls. Existing edited work triggers a replacement confirmation; choosing Cancel preserves it. The **载入互动练习** button can retry. Unchanged imported exercise drafts can be switched without repeated confirmation. Save drafts to the existing lesson library when needed.
4. Review and edit all fields, including the test visibility and pitfall/test associations. Click **发布为当前任务** only when ready. The Notebook remains loaded in the current page after publishing, so the next exercise needs no re-upload. Refreshing or closing the page clears the import.
5. Ordinary code and Markdown retain preview, search, filters and code composition. Unmarked code may be inserted manually; marked exercises load independently to avoid mixing unrelated programs/tests. A reference cell is preview-only; it cannot enter a combination, starter or public description through the import controls.

## Optional Cell Metadata (version 1)

The basic comment is sufficient. You can add tests in the ClassLab teacher editor under **测试用例与易错点** after loading the exercise. To preload them from your file, select the marked Code cell and use your Notebook editor's Cell Metadata view. Add the `classlab` object to that cell's metadata, alongside other cell metadata. The JSON belongs in Cell Metadata. Keep only the C++ code and marker in the source editor.

This example preloads a prompt, one public test, one hidden test and a common pitfall. The starter intentionally uses `> 60` so the public test at `60` guides students toward `>= 60`.

```json
{
  "classlab": {
    "version": 1,
    "role": "exercise",
    "title": "Optional title when comment has no title",
    "description": "Read one integer 0..100. Print PASS for >=60, otherwise FAIL.",
    "testCases": [
      {"name":"Boundary","input":"60","expectedOutput":"PASS","visibility":"public"},
      {"name":"Teacher case","input":"0","expectedOutput":"FAIL","visibility":"hidden"}
    ],
    "pitfalls": [
      {"name":"Exclusive boundary","note":"Trace equality.","needle":"score > 60","testNumber":"1"}
    ]
  }
}
```

| Field | Rule |
| --- | --- |
| version | Optional; if present, must be integer 1. |
| role | Optional exercise; answer/reference reserves the cell for teacher preview. |
| title | Optional nonblank string, at most 53 UTF-16 code units / 160 UTF-8 bytes. Explicit comment title wins; otherwise Metadata title; otherwise original Cell number. |
| description | Optional public text, max 3000 code units / 10000 bytes. |
| testCases | Optional array of 0–12; each requires name (nonblank, 40 code units / 120 bytes), input and expectedOutput (strings, 2700 units / 8192 bytes each, empty allowed), visibility exactly public or hidden. Order determines test number. |
| pitfalls | Optional array of 0–8; name required (60 units / 240 bytes); optional note (300 units / 1200 bytes), needle (160 units / 640 bytes, not whitespace-only), testNumber (string "1" through "12", referring to an existing test, or empty). |
| source | The marker is mandatory; metadata alone cannot turn an ordinary cell into an exercise. Source max 20000 code units / 65536 bytes. |

Unknown classlab fields, invalid types, null in place of optional field values, out-of-range references, oversized fields, unsupported code and conflicting role/marker metadata are not silently ignored. Invalid ClassLab-tagged cells are preview-only with a warning and excluded from the recognized exercise count. Ordinary cells without ClassLab Metadata remain usable. Cell indexes and source are preserved in the browser's model; loading removes only the bare %%cpp wrapper and surrounding leading whitespace.

## Teacher-only information

Keep reference answers in a separate file or mark their Code Cell with `// @classlab answer` (also `// @classlab reference`) as its first nonblank line, optionally after bare %%cpp. For Code or Markdown, `metadata.classlab.role = "answer"` or `"reference"` blocks the import controls, even if the source contains an exercise marker. Do not put solutions or hidden cases into public description or starter source.

Only the selected task title, public description, starter source, test configurations and pitfalls are sent on explicit publication; the existing server's student projection includes only public tests. Hidden result rows include only ordinal labels and status. Teacher pitfalls and hidden case contents do not appear in student task/result data. This does not prevent a teacher from intentionally copying private material into a public field. Keep teacher Notebooks outside public web directories; do not distribute them to students. The repository's authored example and fixture values are synthetic demonstration material, not real private exam cases.

## Full original lecture and replay

- [CS2310 Score Analysis Notebook](../examples/CS2310_Score_Analysis.ipynb) — 74 cells; five marked exercises at original cells 22, 35, 48, 63, 72.
- Instructor-only sample references for the synthetic lesson: [score_analysis_references.json](../examples/score_analysis_references.json). Download the lecture from the repository to the teacher device and upload it from there; the server does not serve this file or its reference JSON through a classroom endpoint.
- Demo uses exact trimmed starter/reference source and exact predefined inputs; free Run accepts only the new exercises' **public** fixture inputs. Formal replay requires the complete ordered fixture input list. Other source or inputs explicitly return no matching data; correct alternative solutions may be unsupported. The legacy tiny synthetic addition demo remains available for compatibility.
- CTest compiles and runs all 27 code cells and 5 separate reference programs in C++20, checks the specified ordinary outputs, public/hidden tests, defective starters and replay data. It only executes trusted repository-authored examples. It does not attest deployment of arbitrary student code.
- Start `bash demo/start_coursework.sh 8082` and use [the coursework demo guide](COURSEWORK_DEMO.md). Ordinary production still requires a verified isolated Judge.
