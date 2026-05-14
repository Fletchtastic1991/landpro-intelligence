name = input('What is your name? ')
print("How's it going?  " + name + '!')
color = input('My name is Python. What is your favorite color? ')
print(color + ' is a nice color!')
number = input('What is your favorite number? ')
print('Your favorite number is ' + number + '.')
if int(number) > 10:
    print('That is a big number!')
elif int(number) < 10:
    print('That is a small number!')
else:
    print('That is a nice number!')
print('I have a question for you. Do you like pizza?')
answer = input('Type yes or no: ')
if answer == 'yes':
    print('I like pizza too!')
else:
    print('That is okay. Pizza is not for everyone.')