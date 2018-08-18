import json

json_file = open('smn.json', 'r')
json_data = json.loads(json_file.read().encode('utf-8'))

for item  in json_data:
    for i in item:
        print(i, item[i])
    print('*' * 8)
	    # print('{0}: {1}'.format(i, item[i]))
