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

class GameState:
	def __init__(self, herohealth, mana, characters, enemy_herohealth, enemy_characters):
		self.herohealth = herohealth
		self.potential_damage = self.calculatePotentialDamage(characters)
		self.number_of_minions = len(characters) - 1 # minus 1 to remove the hero
		self.enemy_herohealth = enemy_herohealth
		self.enemy_number_of_minions = len(enemy_characters) - 1 # minus 1 to remove the hero

	def calculatePotentialDamage(self, characters):
		total = 0

		for character in characters:
			if character.can_attack():
				total += character.atk

		return total

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

	def possibleNextAtk(self):
		result = []
		player = self.game.current_player

		for character in player.characters:
			if character.can_attack():
				result.append((character, Actions.ATTACK))

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

	def possibleNextAction(self):
		result = []
		player = self.game.current_player

		for card in player.hand:
			if card.is_playable():
				result.append((card, Actions.PLAY))

		if player.hero.power.is_usable():
			result.append((player.hero.power, Actions.POWER))

		return result

	def simulatePossibleActions(self, cards_played=[]):
		result = []

		list_of_next_actions = self.possibleNextAction()

		for i in range(0, len(list_of_next_actions)):
			p = self.game.current_player
			opp = p.opponent
			card = list_of_next_actions[i][0]
			type_of_action = list_of_next_actions[i][1]

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

	def move(self, test):
		list_of_actions = test.simulatePossibleActions()
		list_of_atks = test.simulatePossibleAtks()

		for (action, function, param) in self.heuristic:
			if action == Actions.PLAY or Actions.POWER:
				move = function(list_of_actions, param)
				print(move)
			elif action == Actions.ATTACK:
				move = function(list_of_atks, param)
				print(move)

	def interpreter(self, heuristic):
		result = []

		for (action, item, param) in heuristic:
			if item == "min":
				result.append((action, heuristicfunctions.minimum, param))
			elif item == "max":
				result.append((action, heuristicfunctions.maximum, param))

		return result

class GameHandler:
	def __init__(self, test_case, players):
		self.game_tester = test_case
		self.players = players

		cards.db.initialize()

	def run(self):
		self.game_test.start()

		while not self.game_test.game.ended:
			
			self.game_test.game.end_turn()

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

temp = GameHandler([], [])
t = Test()
t.start()

t.game.end_turn()
t.game.end_turn()
t.game.end_turn()
t.game.end_turn()

hai = HeuristicAI([(Actions.PLAY, "max", "potential_damage"), (Actions.ATTACK, "min", "enemy_herohealth")])
hai.move(t)
