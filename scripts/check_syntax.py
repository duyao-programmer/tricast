import py_compile, os, sys

errors = []
for root, dirs, files in os.walk("app"):
    for f in files:
        if f.endswith(".py"):
            path = os.path.join(root, f)
            try:
                py_compile.compile(path, doraise=True)
            except py_compile.PyCompileError as e:
                errors.append(str(e))

if errors:
    print("语法错误:")
    for e in errors:
        print(e)
    sys.exit(1)
else:
    print("所有文件语法检查通过")
