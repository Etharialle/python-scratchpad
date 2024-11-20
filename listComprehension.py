# Write a Python Program to find out common letters between two strings

# test case
string1 = 'NAINA'
string2 = 'REENE'

# 1) Create a list from each string
# 2) Set the list so it is unique
# 3) List comprehension to get common letters

set1 = set(string1)
set2 = set(string2)

commonLetters = {x for x in set1 if x in set2}
print(set1)
print(set2)
print(commonLetters)