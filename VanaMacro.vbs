Set objShell = CreateObject("Shell.Application")
Set objFSO = CreateObject("Scripting.FileSystemObject")
strPath = objFSO.GetParentFolderName(WScript.ScriptFullName)
strPython = strPath & "\.venv\Scripts\pythonw.exe"
objShell.ShellExecute strPython, "main.py", strPath, "runas", 1

