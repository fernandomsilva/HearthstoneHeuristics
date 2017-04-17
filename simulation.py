from enum import Enum
import copy

from hearthstone.enums import *
from fireplace import cards
from fireplace.game import Game
from fireplace.player import Player
import fireplace.cards
from hunter_simple_deck import *

import heuristicfunctions

class Actions(Enum):
	PLAY = 1
	ATTACK = 2
	POWER = 3

class Effects(Enum):
	SUMMON = 1
	HIT = 2
	CUSTOM = 3

class ProtoCharacter:
	def __init__(self, id, atk, health, race, power):
		self.id = id
		self.atk = atk
		self.health = health
		self.race = race
		self.power = power

class CharacterState:
	def __init__(self, char):
		self.id = char.id
		self.atk = char.atk
		self.health = char.health
		self.race = char.race
		if 'data' in char.__dict__:
			self.power = self.buildPowerDict(char.data.scripts)
		else:
			self.power = {'battlecry': [], 'update': []}
	
	def __str__(self):
		return str(self.id) + ": ATK/" + str(self.atk) + " HP/" + str(self.health) + " RACE/" + str(self.race) + " POWER/" + str(self.power)
	
	def buildPowerDict(self, charscript):
		result = {'battlecry': [], 'update': []}
		
		for data in charscript.play:
			if isinstance(data, fireplace.actions.Summon):
				temp_id = data._args[1]
				temp_tags = cards.db[temp_id].tags
				temp_char = ProtoCharacter(temp_id, temp_tags[GameTag.ATK], temp_tags[GameTag.HEALTH], temp_tags[GameTag.CARDRACE],[])
				result['battlecry'].append((Effects.SUMMON, temp_char))
			
			if isinstance(data, fireplace.actions.Hit):
				result['battlecry'].append((Effects.HIT, True, data._args[1]))
			
		for data in charscript.update:
			if data.buff == 'CS2_122e':
				result['update'].append((Effects.CUSTOM, 'Raid Leader'))
			
			if data.buff == 'DS1_175o':
				result['update'].append((Effects.CUSTOM, 'Timber Wolf'))

		return result

class GameState:
	def __init__(self, game):
		player = game.current_player
		opponent = player.opponent
		self.herohealth = player.hero.health
		self.mana = player.mana
		self.potential_damage = self.calculatePotentialDamage(player.characters)
		self.minions = [CharacterState(x) for x in player.characters]
		self.number_of_minions = len(player.characters) - 1 # minus 1 to remove the hero
		self.enemy_herohealth = opponent.hero.health
		self.enemy_minions = [CharacterState(x) for x in opponent.characters]
		self.enemy_number_of_minions = len(opponent.characters) - 1 # minus 1 to remove the hero
		self.updateEffects = self.minionsUpdateEffects()
	
	def __str__(self):
		temp = ""
		temp += "Hero Health: " + str(self.herohealth)
		temp += " Hero Mana: " + str(self.mana)
		temp += " Potential Damage: " + str(self.potential_damage)
		temp += " Minions: " + str(self.minions)
		temp += " Enemy Hero Health: " + str(self.enemy_herohealth)
		temp += " Enemy # of Minions: " + str(self.enemy_number_of_minions)
		
		return temp

	def copy(self, state):
		self.herohealth = state.herohealth
		self.mana = state.mana
		self.potential_damage = state.potential_damage
		self.minions = list(state.minions)
		self.number_of_minions = state.number_of_minions
		self.enemy_herohealth = state.enemy_herohealth
		self.enemy_number_of_minions = state.enemy_number_of_minions
		self.updateEffects = self.minionsUpdateEffects()

	def calculatePotentialDamage(self, characters):
		total = 0

		for character in characters:
			if character.can_attack():
				total += character.atk

		return total

	def minionsUpdateEffects(self):
		result = []

		for minion in self.minions:
			if len(minion.power['update']) > 0:
				for minion_power in minion.power['update']:
					result.append((minion, minion_power[0], minion_power[1]))

		return result

	def activatePower(self, charstate, type):
		for power, effect in charstate.power[type]:
			if power == Effects.SUMMON:
				self.addMinion(effect)

			elif power == Effects.HIT:
				pass

			elif power == Effects.CUSTOM:
				if effect == 'Raid Leader':
					for minion in self.minions:
						if id(minion) != id(charstate):
							minion.atk = minion.atk + 1

				elif effect == 'Timber Wolf':
					for minion in self.minions:
						if id(minion) != id(charstate):
							if minion.race == charstate.race:
								minion.atk = minion.atk + 1

	def addMinion(self, card):
		charstate = CharacterState(card)
		self.minions.append(charstate)
		if len(charstate.power['battlecry']) > 0:
			self.activatePower(charstate, 'battlecry')
		if len(charstate.power['update']) > 0:
			self.activatePower(charstate, 'update')
		self.number_of_minions = self.number_of_minions + 1
		#self.potential_damage = self.calculatePotentialDamage(player.characters)

	def playSpell(self, card, target):
		spellscript = card.data.scripts

		flagHero = True

		for data in spellscript.play:
			if isinstance(data, fireplace.actions.Hit):
				if 'HERO' not in target.id:
					#print(target)
					for minion in self.enemy_minions:
						if minion.id == target.id and minion.atk == target.atk and minion.health == target.health:
							#print('here')
							minion.health = minion.health - data._args[1]
							flagHero = False

					if flagHero:
						for minion in self.minions:
							if minion.id == target.id and minion.atk == target.atk and minion.health == target.health:
								#print('here 2')
								minion.health = minion.health - data._args[1]
								flagHero = False
	
				else:
					#ADD SELF HERO HIT ??????????????????????
					self.enemy_herohealth = self.enemy_herohealth - data._args[1]
	
	def removeEffect(self, minion, opponent=False):
		if opponent:
			source = self.enemy_minions
		else:
			source = self.minions
	
		if not opponent:
			for (effect_minion, minion_power_type, minion_power) in self.updateEffects:
				if id(effect_minion) == id(minion):
					if minion_power_type == Effects.CUSTOM:
						if minion_power == 'Raid Leader':
							for target_minion in source:
								target_minion.atk = target_minion.atk - 1
						
						if minion_power == 'Timber Wolf':
							for target_minion in source:
								if target_minion.race == minion.race:
									target_minion.atk = target_minion.atk - 1
				
					break
		else:
			if len(minion.power['update']) > 0:
				for power_type, power in minion.power['update']:
					if power_type == Effects.CUSTOM:
						if power == 'Raid Leader':
							for target_minion in source:
								target_minion.atk = target_minion.atk - 1
						
						if power == 'Timber Wolf':
							for target_minion in source:
								if target_minion.race == minion.race:
									target.minion.atk = target_minion.atk - 1
	
	def minionAtk(self, character, target):
		attacker = None
		defender = None
		
		for char in self.minions:
			if char.id == character.id and char.atk == character.atk and char.health == character.health:
				attacker = char
				break
		
		for char in self.enemy_minions:
			if char.id == target.id and char.atk == target.atk and char.health == target.health:
				defender = char
				break
		
		if attacker != None and defender != None:
			if 'HERO' in defender.id:
				if target.controller != character.controller:
					self.minionDamage(attacker, defender, hero=True, self_hero=False)
				else:
					self.minionDamage(attacker, defender, hero=True, self_hero=True)
			else:
				self.minionDamage(attacker, defender)
	
			return True
		
		return False
		
	def minionDamage(self, attacker, defender, hero=False, self_hero=False):
		if hero:
			if self_hero:
				self.herohealth = self.herohealth - attacker.atk
			else:
				self.enemy_herohealth = self.enemy_herohealth - attacker.atk
		else:
			defender.health = defender.health - attacker.atk
			attacker.health = attacker.health - defender.atk
	
		self.updateState()
	
	def updateState(self):
		list_of_minions_to_remove = []
	
		for minion in self.minions:
			if minion.health <= 0:
				list_of_minions_to_remove.append(minion)

		for minion in list_of_minions_to_remove:
			self.minions.remove(minion)
			self.removeEffect(minion)

		list_of_minions_to_remove = []
	
		for minion in self.enemy_minions:
			if minion.health <= 0:
				list_of_minions_to_remove.append(minion)

		for minion in list_of_minions_to_remove:
			self.enemy_minions.remove(minion)
			#self.removeEffect(minion)

		self.number_of_minions = len(self.minions) - 1
		self.enemy_number_of_minions = len(self.enemy_minions) - 1


class Test:
	def __init__(self):
		self.player1 = None
		self.hero1 = None
		self.deck1 = []

		self.player2 = None
		self.hero2 = None
		self.deck2 = []

		self.game = None

	def start(self):
		self.hero1 = CardClass.HUNTER.default_hero
		self.hero2 = CardClass.HUNTER.default_hero
		self.deck1 = list(hunter_simple_deck)
		self.deck2 = list(hunter_simple_deck)
		self.player1 = Player("one", self.deck1, self.hero1)
		self.player2 = Player("two", self.deck2, self.hero2)
		self.game = Game(players=(self.player1, self.player2))
		self.game.start()
		self.skipMulligan()

	def skipMulligan(self):
		self.player1.choice.choose()
		self.player2.choice.choose()

	def possibleNextAtkLight(self, used=[]):
		result = []
		player = self.game.current_player

		for x in range(0, len(player.characters)):
			if x not in used:
				character = player.characters[x]
				if character.can_attack():
					result.append((character, Actions.ATTACK))

		return result

	def possibleNextAtk(self):
		result = []
		player = self.game.current_player

		for character in player.characters:
			if character.can_attack():
				result.append((character, Actions.ATTACK))

		return result

	def simulatePossibleAtksLight(self, cards_atk=[], gstate=None, cards_used=[]):
		if gstate == None:
			gstate = GameState(self.game)

		result = []

		list_of_next_atks = self.possibleNextAtkLight(cards_used)

		for (character, type_of_action) in list_of_next_atks:
			p = self.game.current_player
			opp = p.opponent

			for target in character.targets:
				temp_state = GameState(self.game)
				temp_state.copy(gstate)

				#target_dict = {'card': target, 'atk': target.atk, 'health': target.health, 'opponent': True if target.controller.first_player != p.first_player else False}

				temp_state.minionAtk(character, target)

				result.append((cards_atk + [(character, target)], temp_state))
				result.extend(self.simulatePossibleAtksLight(cards_atk + [(character, target)], temp_state, cards_used + [p.characters.index(character)]))

		return result


	def simulatePossibleAtks(self, cards_atk=[]):
		result = []

		list_of_next_atks = self.possibleNextAtk()

		for i in range(0, len(list_of_next_atks)):
			p = self.game.current_player
			opp = p.opponent

			index_of_char = p.characters.index(list_of_next_atks[i][0])

			list_of_targets = list_of_next_atks[i][0].targets

			for j in range(0, len(list_of_targets)):
				copy_test = Test()
				copy_test.game = copy.deepcopy(self.game)

				target = list_of_targets[j]

				target_dict = {'card': target, 'atk': target.atk, 'health': target.health, 'opponent': True if target.controller.first_player != p.first_player else False}

				if target_dict['opponent'] == True:
					index_of_target = opp.characters.index(target)
					copy_test.game.current_player.characters[index_of_char].attack(target=copy_test.game.current_player.opponent.characters[index_of_target])
				else:
					index_of_target = p.characters.index(target)
					copy_test.game.current_player.characters[index_of_char].attack(target=copy_test.game.current_player.characters[index_of_target])

				player = copy_test.game.current_player
				opponent = player.opponent
				result.append((cards_atk + [(p.characters[index_of_char], target_dict)], GameState(player.hero.health, player.mana, player.characters, opponent.hero.health, opponent.characters)))
				result.extend(copy_test.simulatePossibleAtks(cards_atk + [(p.characters[index_of_char], target_dict)]))

		return result

	def possibleNextActionLight(self, used=[]):
		result = []
		player = self.game.current_player

		for x in range(0, len(player.hand)):
			if x not in used:
				card = player.hand[x]
				if card.is_playable():
					result.append((x, Actions.PLAY))
		
		if player.hero.power.is_usable() and player.hero.power not in used:
			result.append((player.hero.power, Actions.POWER))
		
		return result	
	
	def possibleNextAction(self):
		result = []
		player = self.game.current_player

		for card in player.hand:
			if card.is_playable():
				result.append((card, Actions.PLAY))

		if player.hero.power.is_usable():
			result.append((player.hero.power, Actions.POWER))

		return result
	
	def simulatePossibleActionsLight(self, cards_played=[], gstate=None, cards_used=[]):
		if gstate == None:
			gstate = GameState(self.game)
		
		current_mana = self.game.current_player.mana
		
		result = []
		
		list_of_possible_actions = self.possibleNextActionLight(cards_used)
		
		for (card_index, type_of_action) in list_of_possible_actions:
			if (type_of_action == Actions.PLAY):
				card = self.game.current_player.hand[card_index]
				if isinstance(card, fireplace.card.Minion):
					temp_state = GameState(self.game)
					temp_state.copy(gstate)
					temp_state.addMinion(card)
					
					self.game.current_player.__dict__['_max_mana'] = self.game.current_player.__dict__['_max_mana'] - card.cost
					
					result.append((cards_played + [card], temp_state))
					result.extend(self.simulatePossibleActionsLight(cards_played + [card], temp_state, cards_used + [card_index]))
		
					self.game.current_player.__dict__['_max_mana'] = current_mana

				if isinstance(card, fireplace.card.Spell):
					if len(card.targets) > 0:
						for target in card.targets:
							temp_state = GameState(self.game)
							temp_state.copy(gstate)

							if card.id == 'GAME_005': #THE COIN							
								self.game.current_player.__dict__['_max_mana'] = self.game.current_player.__dict__['_max_mana'] + 1

								temp_state.mana = self.game.current_player.mana
								
								result.append((cards_played + [card], temp_state))
								result.extend(self.simulatePossibleActionsLight(cards_played + [card], temp_state, cards_used + [card_index]))
					
								self.game.current_player.__dict__['_max_mana'] = current_mana

							else:
								self.game.current_player.__dict__['_max_mana'] = self.game.current_player.__dict__['_max_mana'] - card.cost

								temp_state.mana = self.game.current_player.mana
								#target_dict = {'card': target, 'atk': target.atk, 'health': target.health, 'opponent': True if target.controller.first_player != self.game.current_player.first_player else False}

								temp_state.playSpell(card, target)
								
								result.append((cards_played + [(card, target)], temp_state))
								result.extend(self.simulatePossibleActionsLight(cards_played + [(card, target)], temp_state, cards_used + [card_index]))
					
								self.game.current_player.__dict__['_max_mana'] = current_mana

			if (type_of_action == Actions.POWER):
				temp_state = GameState(self.game)
				temp_state.copy(gstate)
				if self.game.current_player.hero.power.id == 'DS1h_292':
					temp_state.enemy_herohealth = temp_state.enemy_herohealth - 2
					
				self.game.current_player.__dict__['_max_mana'] = self.game.current_player.__dict__['_max_mana'] - self.game.current_player.hero.power.cost
	
				temp_state.mana = self.game.current_player.mana

				result.append((cards_played + [card_index], temp_state))
				result.extend(self.simulatePossibleActionsLight(cards_played + [card_index], temp_state, cards_used + [card_index]))

				self.game.current_player.__dict__['_max_mana'] = self.game.current_player.__dict__['_max_mana'] + self.game.current_player.hero.power.cost
		
		self.game.current_player.__dict__['_max_mana'] = current_mana
		
		return result

	def simulatePossibleActions(self, cards_played=[]):
		result = []

		list_of_next_actions = self.possibleNextAction()

		for i in range(0, len(list_of_next_actions)):
			p = self.game.current_player
			opp = p.opponent
			card = list_of_next_actions[i][0]
			type_of_action = list_of_next_actions[i][1]
			target_flag = False

			if type_of_action == Actions.PLAY:
				index_of_card = p.hand.index(list_of_next_actions[i][0])

				target_flag = False
				if len(card.targets) > 0:
					target_flag = True
					list_of_targets = card.targets

					for j in range(0, len(list_of_targets)):
						copy_test = Test()
						copy_test.game = copy.deepcopy(self.game)

						target = list_of_targets[j]
						target_dict = {'card': target, 'atk': target.atk, 'health': target.health, 'opponent': True if target.controller.first_player != p.first_player else False}

						if target_dict['opponent'] == True:
							index_of_target = opp.characters.index(target)
							copy_test.game.current_player.hand[index_of_card].play(target=copy_test.game.current_player.opponent.characters[index_of_target])
						else:
							index_of_target = p.characters.index(target)
							copy_test.game.current_player.hand[index_of_card].play(target=copy_test.game.current_player.characters[index_of_target])

						player = copy_test.game.current_player
						opponent = player.opponent
						result.append((cards_played + [(card, target_dict)], GameState(player.hero.health, player.mana, player.characters, opponent.hero.health, opponent.characters)))
						result.extend(copy_test.simulatePossibleAtks(cards_played + [(card, target_dict)]))

				else:
					copy_test = Test()
					copy_test.game = copy.deepcopy(self.game)

					temp_list_of_next_actions = copy_test.possibleNextAction()

					temp_list_of_next_actions[i][0].play()


			elif type_of_action == Actions.POWER:
				copy_test = Test()
				copy_test.game = copy.deepcopy(self.game)

				copy_test.game.current_player.hero.power.use()

			if not target_flag:
				player = copy_test.game.current_player
				opponent = player.opponent

				result.append((cards_played + [card], GameState(player.hero.health, player.mana, player.characters, opponent.hero.health, opponent.characters)))
				result.extend(copy_test.simulatePossibleActions(cards_played + [card]))

		return result

		'''
		result = []

		list_of_next_actions = self.possibleNextAction()

		for (card, type_of_action) in list_of_next_actions:
			copy_test = Test()
			copy_test.game = copy.deepcopy(self.game)
			
			player = copy_test.game.current_player
			opponent = player.opponent
			target_flag = False

			if type_of_action == Actions.PLAY:
				if len(card.targets) > 0:
					target_flag = True
					for target in card.targets:
						copy_test_target = Test()
						copy_test_target.game = copy.deepcopy(self.game)
						#copy_test_target.game.players = (Player("one", self.deck1, self.hero1), Player("two", self.deck2, self.hero2))

						for card_copy_t in copy_test_target.game.current_player.hand:
							if card == card_copy_t:
								#if target == player:
								#	target = copy_test_target.game.current_player
								#if target == opponent:
								#	target = copy_test_target.game.current_player.opponent

								target_dict = {'card': target, 'atk': target.atk, 'health': target.health, 'opponent': True if target.controller.first_player != card_copy_t.game.current_player.first_player else False}
								card_copy_t.play(target=target)

								result.append((cards_played + [(card, target_dict)], GameState(player.hero.health, player.mana, player.characters, opponent.hero.health, opponent.characters)))
								result.extend(copy_test_target.simulatePossibleActions(cards_played + [(card_copy_t, {'card': target, 'atk': target.atk, 'health': target.health, 'opponent': True if target.controller != player else False})]))

								break

				else:
					for card_copy in copy_test.game.current_player.hand:
						if card == card_copy:
							card_copy.play()
							break

			elif type_of_action == Actions.POWER:
				copy_test.game.current_player.hero.power.use()

			if not target_flag:
				result.append((cards_played + [card], GameState(player.hero.health, player.mana, player.characters, opponent.hero.health, opponent.characters)))
				result.extend(copy_test.simulatePossibleActions(cards_played + [card]))

		return result
		'''
class AI:
	pass

class HeuristicAI:
	def __init__(self, heuristic):
		self.heuristic = self.interpreter(heuristic)

	def interpreter(self, heuristic):
		result = []

		for (action, item, param) in heuristic:
			if item == "min":
				result.append((action, heuristicfunctions.minimum, param))
			elif item == "max":
				result.append((action, heuristicfunctions.maximum, param))

		return result

	def move(self, test):
		#list_of_actions = test.simulatePossibleActions()
		#list_of_atks = test.simulatePossibleAtks()
		list_of_actions = test.simulatePossibleActionsLight()
		print (list_of_actions)
		print(test.game.current_player.characters)
		print(test.game.current_player.opponent.characters)
		list_of_atks = test.simulatePossibleAtksLight()
		print (list_of_atks)

		for (action, function, param) in self.heuristic:
			if action == Actions.PLAY or action == Actions.POWER:
				if len(list_of_actions) > 0:
					move = function(list_of_actions, param)
					if len(move) == 1:
						self.play(move[0][0], test.game)
					else:
						temp = heuristicfunctions.minimum(move, "mana")
						self.play(temp[0][0], test.game)

			elif action == Actions.ATTACK:
				if len(list_of_atks) > 0:
					move = function(list_of_atks, param)
					if len(move) == 1:
						self.attack(move[0][0], test.game)
					else:
						self.attack(move[0][0], test.game)

	def play(self, move, game):
		for action in move:
			if (isinstance(action, fireplace.card.HeroPower)):
				game.current_player.hero.power.use()
			else:
				if not isinstance(action, tuple):
					action.play()
				else:
					action[0].play(target=action[1])

				'''
				for card in game.current_player.hand:
					if not isinstance(action, tuple):
						if card == action:
							card.play()
							break
					else:
						actor = action[0]
						target = action[1]

						char_pool = []
						
						if target['opponent']:
							char_pool = game.current_player.opponent.characters
						else:
							char_pool = game.current_player.characters
						
						for char in char_pool:
							if char == target['card'] and char.atk == target['atk'] and char.health == target['health']:
								card.play(target=char)
								break
				'''
	
	def attack(self, move, game):
		for (atk_char, target) in move:
			atk_char.attack(target=target)
			'''
			if target['opponent']:
				char_pool = game.current_player.opponent.characters
			else:
				char_pool = game.current_player.characters

			if (isinstance(atk_char, fireplace.card.HeroPower)):
				for char in char_pool:
					if char == target['card'] and char.atk == target['atk'] and char.health == target['health']:
						game.current_player.hero.power(target=char)
						break
			else:
				for self_char in game.current_player.characters:
					if self_char == atk_char and self_char.can_attack():
						for char in char_pool:
							if char == target['card'] and char.atk == target['atk'] and char.health == target['health']:
								self_char.attack(target=char)
								break
						
						break
			'''

class GameHandler:
	def __init__(self, test_case, players):
		self.game_tester = test_case
		self.players = players

		cards.db.initialize()

	def run(self):
		self.game_tester.start()

		current_player = 0
		
		while not self.game_tester.game.ended:
			self.players[current_player].move(self.game_tester)
			self.game_tester.game.end_turn()
			
			current_player = (current_player + 1) % 1

'''
self.player1.hero.power.is_usable()
self.player1.hero.power.use()
self.player1.card.must_choose_one
self.player1.card.targets
self.player1.card.is_playable()
self.player1.card.play()
self.player1.card.play(target=<target>) => self.player1.choice.choose(choice)  choice = [self.player1.choice.cards]
self.player1.characters
self.player1.characters[0].can_attack()
self.player1.characters[0].targets
self.player1.characters[0].attack(target)
self.game.end_turn()
'''

def testrun():
	t.start()
	t.game.end_turn()
	for card in t.game.current_player.hand:
		if len(card.targets) == 0:
			if card.is_playable():
				card.play()
	t.game.end_turn()
	t.game.end_turn()
	for card in t.game.current_player.hand:
		if len(card.targets) == 0:
			if card.is_playable():
				card.play()
	t.game.end_turn()
	t.game.end_turn()
	t.game.end_turn()	

	h = t.simulatePossibleActionsLight()

#t = Test()
'''
temp = GameHandler(t,[])
t.start()
for card in t.game.current_player.hand:
	if len(card.targets) == 0:
		if card.is_playable():
			card.play()
t.game.end_turn()
for card in t.game.current_player.hand:
	if len(card.targets) == 0:
		if card.is_playable():
			card.play()
t.game.end_turn()
for card in t.game.current_player.hand:
	if len(card.targets) == 0:
		if card.is_playable():
			card.play()
t.game.end_turn()
for card in t.game.current_player.hand:
	if len(card.targets) == 0:
		if card.is_playable():
			card.play()
t.game.end_turn()
t.game.end_turn()
t.game.end_turn()
'''
#h = t.simulatePossibleActionsLight()
#t.start()

hai = HeuristicAI([(Actions.PLAY, "max", "potential_damage"), (Actions.ATTACK, "min", "enemy_herohealth")])
hai2 = HeuristicAI([(Actions.PLAY, "max", "number_of_minions"), (Actions.ATTACK, "min", "enemy_number_of_minions")])
temp = GameHandler(Test(), [hai, hai2])
temp.run()
