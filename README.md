# broadridge_spell_checker

Spelling checker. It reads a dictionary and a text section from standard input and writes the corrected text to standard output.

The dictionary is free-format words, ended by a line that is exactly `===`. Text lines follow, ended by another `===` line. Whitespace inside each text line is preserved.

## Compile

Requires a C++17 compiler. Microsoft Visual Studio 2022 and GCC 14 both work. No external libraries are needed.

`cl` is not on `PATH` in a normal Command Prompt or PowerShell. Load the Visual Studio build environment first.

Command Prompt, from this directory:

```
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat"
cl /std:c++17 /permissive- /W4 /EHsc /O2 spellchecker.cpp
```

PowerShell:

```
cmd /c "call `"C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat`" && cl /std:c++17 /permissive- /W4 /EHsc /O2 spellchecker.cpp"
```

Either command produces `spellchecker.exe` in this directory.

You can also open **x64 Native Tools Command Prompt for VS 2022** from the Start menu, change to this directory, and run `cl /std:c++17 /permissive- /W4 /EHsc /O2 spellchecker.cpp` there. In that prompt `cl` is already on `PATH`.

GCC:

```
g++ -std=c++17 -O2 -o spellchecker spellchecker.cpp
```

## Run

Pass the input on standard input and read the corrected text from standard output.

Windows:

```
spellchecker.exe < input.txt
```

GCC build:

```
./spellchecker < input.txt
```
