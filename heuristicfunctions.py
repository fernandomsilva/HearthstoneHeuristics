def minimum(input_list, attr):
	return min(input_list, key = lambda t:t[1].__dict__[attr])

def maximum(input_list, attr):
	return max(input_list, key = lambda t:t[1].__dict__[attr])

#print(list_of_actions)

#print(list_of_actions[0][1])
#print(min(list_of_actions, key = lambda t:t[1].__dict__["enemy_number_of_minions"]))