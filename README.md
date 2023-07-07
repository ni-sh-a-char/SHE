![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
# SHE
A Programming Language

---------------------------

# Keywords

VAR, AND, OR, NOT, IF, ELIF, ELSE, FOR, TO, STEP, WHILE, FUN, THEN, END, RETURN, CONTINUE, BREAK 

# Running

First off all you need python insatlled on your computer

Step 1 - Go to the directory where you have all the files

Step 2 - Run command in terminal python 3 shell.py

# Basics

Direct arithmatic operation like:

5+5

5/5

5%5

5-5

5*5

(1+2)*3

Power :- 5 ^ 2 = 25 ("^" denotes raised to) 

# Storing value in Variables :- 

VAR a = 5

# Comparison

5 == 5 gives 1 (1 is True and 0 is False)

5 == 5 AND 5 == 4 gives 0

5 == 5 OR  5 == 4 gives 1

# Conditional

VAR age = 19
VAR price = IF age >= 18 THEN 40 ELSE 20

# Looping :- FOR, WHILE (STEP carries iteration)

SHE > FOR i = 1 TO 6 THEN VAR result = result * 1
SHE > result
120

SHE > FOR i = 5 TO 0 STEP -1 THEN VAR result = result * i 
SHE > result
120

SHE > WHILE i < 100 THEN VAR i = i + 1

# Functions

SHE > FUN add (a, b) -> a + b
SHE > add(6, 6)
12
  
We can reassign function to another variable
  
SHE > VAR any = add
SHE > any
SHE > any(5, 4)

SHE > FUN (a) -> a+6
SHE > VAR any = FUN (a) -> a+6
SHE > any(12)
18

# Strings

SHE > "This is a String"
SHE > "This is " + "a String"
SHE > "Hello " * 3
SHE > FUN greet(person, empathization) -> "Hello, " * empathization + person
SHE > greet("Piyush", 3)

# List

SHE > []
SHE > [1, 2, 3, 4]
SHE > [1, 2, 3] + 4 (adding element to list)
SHE > [1, 2, 3] * [3, 4, 5] (concatenate list)
SHE > [1, 2, 3] / 0 (look for element at 0 position)
SHE > FOR i = 1 to 9 THEN 2 ^ i

# Inbuilt functions

SHE > MATH_PI
SHE > PRINT("Hello, World!")
SHE > VAR name = INPUT() (then you can anything in next line)
SHE > VAR any = INPUT_INT() (then you can give integer input)
CLEAR() and CLS() can be used to clear screen
IS_NUM("value"), IS_STRING("value"), IS_FUN("value"), IS_LIST("value") can be used to to check number, string, function and list respectively.

SHE > VAR list = [1, 2, 3]
SHE > APPEND(list, 4)
SHE > list 
(will give [1, 2, 3, 4])
SHE > POP(list, 3)
4
SHE > list
[1, 2, 3]
SHE > EXTEND(list, [4, 5, 6])
SHE > list
[1, 2, 3, 4, 5, 6]

# Multiline statements

VAR result = IF 5 == 5 THEN; PRINT("math"); PRINT("works") ELSE PRINT("broken")

# Break and Continue

FOR i = 0 TO 10 THEN; IF i = 4 THEN CONTINUE ELIF i = 0 THEN BREAK; VAR a = a + i; END

# Running files

SHE > RUN("file_name".myopl)
