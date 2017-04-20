import random

def minimum(input_list, attr):
	#value = min(input_list, key = lambda t:t[1].__dict__[attr]) 
	value = min([x[1].__dict__[attr] for x in input_list])
	return [x for x in input_list if x[1].__dict__[attr] == value]

def maximum(input_list, attr):
	#value = max(input_list, key = lambda t:t[1].__dict__[attr])
	value = max([x[1].__dict__[attr] for x in input_list])
	return [x for x in input_list if x[1].__dict__[attr] == value]

def random(input_list, attr):
	value = max([x[1].__dict__[attr] for x in input_list])
	return [random.choice([x for x in input_list if x[1].__dict__[attr] == value])]

#print(list_of_actions)

#print(list_of_actions[0][1])
#print(min(list_of_actions, key = lambda t:t[1].__dict__["enemy_number_of_minions"]))