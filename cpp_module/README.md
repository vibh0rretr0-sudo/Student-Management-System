# cpp_module — compute engine

`sms_engine.cpp` compiles to a single binary with three modes, invoked by Python via subprocess with TSV-style delimited text on stdin and results on stdout:

```
sms_engine attendance <  attendance_input.txt
sms_engine grades     <  grades_input.txt
sms_engine rank       <  rank_input.txt
```

Why C++ here: the three jobs are pure computation over in-memory data (no I/O beyond stdin/stdout), making them a clean, explainable module boundary. Python owns persistence; C++ owns the math (grade %, attendance eligibility, ranking sort).

Build:
```
python scripts/build_cpp.py
```
(uses g++ with `-std=c++14 -Wall -Wextra`; warnings are enabled and fixed before any build is accepted)
