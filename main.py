from list_helper import next_number

a = [1, 3, 4, 5, 7]

for i in range(12):
    a.sort()
    print(a)
    a.append(next_number(a, start_from=1))

