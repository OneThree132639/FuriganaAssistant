import itertools
import logging
import os
import pandas as pd
import re

from typing import (
	Callable, Collection, Generator, List, Literal, Optional, Tuple
)

class MultipleGobiError(Exception): 
	pass

class AutoDivisionDisabledError(Exception): 
	pass

class AutoDivisionChoiceOverflowError(Exception): 
	pass

class Token0: 
	def __init__(self, jp: str, kana: Optional[str] = None, alignment: int = 0): 
		self.jp = jp
		self.kana = kana
		self.alignment = alignment

	def __str__(self) -> str: 
		return "Token0(jp: {}, kana: {}, alignment: {})".format(self.jp, self.kana, self.alignment)

class Token1: 
	def __init__(self, jp: str, up_kana: Optional[str] = None, down_kana: Optional[str] = None): 
		self.jp = jp
		self.up_kana = up_kana
		self.down_kana = down_kana

	def __str__(self) -> str: 
		return "Token1(jp: {}, up_kana: {}, down_kana: {})".format(self.jp, self.up_kana, self.down_kana)
	
class Token2: 
	def __init__(self, jp: str, kana: Optional[str] = None, is_skip: bool = False): 
		self.jp = jp
		self.kana = kana
		self.is_skip = is_skip

	def __str__(self) -> str: 
		return "Token2(jp: {}, kana: {})".format(self.jp, self.kana)


class Term: 

	PATTERNS = {
		"remove_gobi": re.compile("^(.+)(?<!\\$)\\*.*$"), 
		"is_gobi_exists": re.compile("^.+(?<!\\$)(\\*).+$"), 
		"get_gobi": re.compile("^.+(?<!\\$)\\*(.*)$"), 
		"div_remove_/": re.compile("(?<!\\$)/"), 
		"div_remove_\\": re.compile("(?<!\\$)\\\\"), 
		"div_remove_*": re.compile("(?<!\\$)\\*"), 
		"div_split_/": re.compile("(?<!\\$)/"), 
		"div_split_\\": re.compile("(?<!\\$)\\\\"),
		"div_split_*": re.compile("(?<!\\$)\\*")
	}

	def __init__(self, japanese: str, kana: str, 
			div0: str, div1: str, term_type: str, priority: int, 
		): 
		self.jp = japanese
		self.kana = kana
		self.div0 = div0
		self.div1 = div1
		self.term_type = term_type
		self.pri = priority
		if not self.is_valid(0) or not self.is_valid(1): 
			raise ValueError((
				"[Term] Illegal values to create a Term object: "
				"{}. "
			).format(self))
		
	@classmethod
	def is_valid_transfer(cls, origin_str) -> bool: 
		i = 0
		while i < len(origin_str): 
			if origin_str[i] == "$": 
				if i + 1 < len(origin_str) and origin_str[i + 1] in ("/", "\\", "*", "$"): 
					i += 2
				else: 
					return False
			i += 1
		return True
		
	@classmethod	
	def div_remove(cls, origin_str: str, div_char: Literal["/", "\\", "*"]) -> str: 
		pattern = Term.PATTERNS["div_remove_{}".format(div_char)]
		return re.sub(pattern, "", origin_str)
	
	@classmethod
	def div_split(cls, origin_str: str, div_char: Literal["/", "\\", "*"]) -> List[str]: 
		pattern = Term.PATTERNS["div_split_{}".format(div_char)]
		return re.split(pattern, origin_str)
	
	@classmethod
	def is_jp_str(cls, s: str) -> bool: 
		for c in s: 
			if (
				not Term.is_cjk_unified(c) and not Term.is_kana(c) and 
				not str.isdigit(c) and not c in (".", "-", "+")
			): 
				return False
		return True
	
	@classmethod
	def is_jp_valid_str(cls, s: str) -> bool: 
		for c in s: 
			if not Term.is_jp_str(c) and not c in ("/", "\\", "*"): 
				return False
		return True

	def is_valid(self, div_type: Literal[0, 1]) -> bool: 
		if not all(Term.is_valid_transfer(s) for s in (self.jp, self.kana, self.div0, self.div1)): 
			return False
		
		if self.term_type not in ("英語", "固有"):
			if not all(Term.is_jp_valid_str(s) for s in (self.jp, self.kana)): 
				return False

		div_char = ("/", "\\")
		div = [self.div0, self.div1]
		jp = Term.div_remove(self.jp, div_char[1 - div_type])
		kana = Term.div_remove(self.kana, div_char[1 - div_type])
		division = Term.div_remove(div[div_type], div_char[1 - div_type])

		gobi_exists = [self.is_gobi_exists(jp), self.is_gobi_exists(kana), self.is_gobi_exists(division)]
		if self.term_type in ("名詞", "固有"): 
			if any(gobi_exists): 
				logging.warning((
					"[Term.is_valid] Type is \"名詞\" while gobi exists. "
				))
				return False
		elif self.term_type == "カ変": 
			if jp != "来る" or kana != "くる" or division != "0": 
				logging.warning((
					"[Term.is_valid] Type is \"カ変\" while jp, kana, division are not \"来る\", \"くる\", \"0\". "
				))
				return False
			else: 
				return True
		elif self.term_type == "英語": 
			if any(gobi_exists): 
				logging.warning((
					"[Term.is_valid] Type is \"英語\" while gobi exists. "
				))
				return False
			div_flag = ((division == "1" and div_type == 0) or (division == "0" and div_type == 1))
			en_valid: Callable[[str], bool] = lambda s: all(c.isalpha() or c == "\'" for c in s)
			return (en_valid(jp) and div_flag)
		else: 
			if not all(gobi_exists): 
				logging.warning((
					"[Term.is_valid] Type with katsuyou while at least one gobi doesn't exist. " 
				))
				return False
			try: 
				jp_gobi = self.get_gobi(jp)
				kana_gobi = self.get_gobi(kana)
				division_gobi = self.get_gobi(division)
			except MultipleGobiError: 
				logging.warning((
					"[Term.is_valid] Multiple gobi in one of jp, kana, division. "
				))
				return False
			if (jp_gobi != kana_gobi or division_gobi != "-1"): 
				logging.warning((
					"[Term.is_valid] Gobi doesn't match. "
				))
				return False
			match self.term_type: 
				case "五段": 
					if jp_gobi not in ["う", "く", "ぐ", "す", "つ", "ぬ", "ぶ", "む", "る"]: 
						logging.warning((
							"[Term.is_valid] Invalid gobi for type \"五段\". "
						))
						return False
				case "上下": 
					if jp_gobi != "る": 
						logging.warning((
							"[Term.is_valid] Invalid gobi for type \"上下\". "
						))
						return False
				case "サ変": 
					if jp_gobi != "する": 
						logging.warning((
							"[Term.is_valid] Invalid gobi for type \"サ変\". "
						))
						return False
				case "形容": 
					if jp_gobi != "い": 
						logging.warning((
							"[Term.is_valid] Invalid gobi for type \"形容\". "
						))
						return False
				case _: 
					logging.warning((
						"[Term.is_valid] Invalid type. "
					))
					return False
			jp = self.remove_gobi(jp)
			kana = self.remove_gobi(kana)
			division = self.remove_gobi(division)

		jp_list = Term.div_split(jp, div_char[div_type])
		kana_list = Term.div_split(kana, div_char[div_type])
		div_list = Term.div_split(division, div_char[div_type])
		if len(jp_list) != len(kana_list) or len(jp_list) != len(div_list): 
			logging.warning((
				"[Term.is_valid] Length of jp, kana, division are not equal. \n"
				"jp: {}, kana: {}, division: {}"
			).format(len(jp_list), len(kana_list), len(div_list)))
			return False
		for i in range(len(jp_list)): 
			jp_elem = jp_list[i]
			kana_elem = kana_list[i]
			div_elem = div_list[i]
			is_all_kana = all([self.is_kana(c) for c in jp_elem])
			is_not_all_kana = all([not self.is_kana(c) for c in jp_elem])
			if self.term_type != "固有": 
				if is_all_kana: 
					if is_not_all_kana: 
						logging.warning((
							"[Term.is_valid] Japanese contains kana. "
						))
						return False
					else: 
						if jp_elem != kana_elem or div_elem != "-1": 
							logging.warning((
								"[Term.is_valid] Japanese, Kana, Division don't match. "
							))
							return False
				else: 
					if is_not_all_kana: 
						if div_elem not in ("0", "1", "2"): 
							logging.warning((
								"[Term.is_valid] Division is not valid. "
							))
							return False
					else: 
						logging.warning((
							"[Term.is_valid] Impossible case occurred. "
						))
						return False
			else: 
				if div_elem not in ("-1", "0", "1", "2"): 
					logging.warning((
						"[Term.is_valid] Division is not valid. "
					))
					return False
		return True

	@classmethod
	def is_hiragana(cls, c: str) -> bool: 
		if len(c) != 1: 
			raise ValueError((
				"[Term.is_hiragana]"
				"The length of input value c: {} is not 1. "
			).format(c))
		return 12353 <= ord(c) <= 12436
	
	@classmethod
	def is_katakana(cls, c: str) -> bool:
		if len(c) != 1: 
			raise ValueError((
				"[Term.is_katakana]"
				"The length of input value c: {} is not 1. "
			).format(c))
		return (12449 <= ord(c) <= 12538 or ord(c) == 12540)
	
	@classmethod
	def is_kana(cls, c: str) -> bool:
		if len(c) != 1: 
			raise ValueError((
				"[Term.is_kana]"
				"The length of input value c: {} is not 1. "
			).format(c))
		return cls.is_hiragana(c) or cls.is_katakana(c)

	def to_dict(self) -> dict: 
		return {
			"Japanese": self.jp, 
			"Kana": self.kana, 
			"Division0": self.div0, 
			"Division1": self.div1, 
			"Type": self.term_type, 
			"Priority": self.pri
		}

	@classmethod
	def remove_seps(cls, origin_str: str) -> str: 
		for div_char in ("/", "\\", "*"): 
			origin_str = Term.div_remove(origin_str, div_char)
		for trans_str, trans_obj in (("${}".format(c), c) for c in ("/", "\\", "*", "$")): 
			origin_str = origin_str.replace(trans_str, trans_obj)
		return origin_str
	
	@classmethod
	def remove_gobi(cls, origin_str: str) -> str: 
		pattern = Term.PATTERNS["remove_gobi"]
		result = re.match(pattern, origin_str)
		if result is None:
			return origin_str
		if result.lastindex is not None and result.lastindex > 1: 
			raise MultipleGobiError((
				"[Term.get_gobi] This str {} has more than one gobi(seperated by \"*\"). "
			).format(origin_str))
		return result.group(1)
	
	@classmethod
	def is_gobi_exists(cls, origin_str: str) -> bool: 
		pattern = Term.PATTERNS["is_gobi_exists"]
		result = re.match(pattern, origin_str)
		if result is None: 
			return False
		else: 
			if result.lastindex is None:
				raise ValueError((
					"[Term.is_gobi_exists] result.lastindex is None. "
				).format(origin_str))
			elif result.lastindex > 1: 
				raise MultipleGobiError((
					"[Term.get_gobi] This str {} has more than one gobi(seperated by \"*\"). "
				).format(origin_str))
			return True
	
	@classmethod
	def get_gobi(cls, origin_str: str) -> str: 
		pattern = Term.PATTERNS["get_gobi"]
		result = re.match(pattern, origin_str)
		if result is None: 
			raise ValueError((
				"[Term.get_gobi] This str {} has no gobi(seperated by \"*\"). "
			).format(origin_str))
		if result.lastindex is not None and result.lastindex > 1: 
			raise MultipleGobiError((
				"[Term.get_gobi] This str {} has more than one gobi(seperated by \"*\"). "
			).format(origin_str))
		return result.group(1)

	def re_pattern(self) -> str: 
		match self.term_type: 
			case "名詞": 
				return "^({})(.*)$".format(self.remove_seps(self.jp))
			case "固有": 
				s = self.remove_seps(self.jp)
				for dec_c in ("\\", "$", "(", ")", "*", "?", "+", ".", "[", "]", "{", "}", "|", "^"): 
					s = s.replace(dec_c, "\\{}".format(dec_c))
				return "^({})(.*)$".format(s)
			case "五段": 
				gobi_dic = {
					"う": ["わ", "い", "う", "え", "お", "っ"], 
					"く": ["か", "き", "く", "け", "こ", "い"], 
					"ぐ": ["が", "ぎ", "ぐ", "げ", "ご", "い"], 
					"す": ["さ", "し", "す", "せ", "そ"], 
					"つ": ["た", "ち", "つ", "て", "と", "っ"], 
					"ぬ": ["な", "に", "ぬ", "ね", "の", "ん"], 
					"ぶ": ["ば", "び", "ぶ", "べ", "ぼ", "ん"], 
					"む": ["ま", "み", "む", "め", "も", "ん"], 
					"る": ["ら", "り", "る", "れ", "ろ", "っ"], 
				}
				gokan = self.remove_seps(self.remove_gobi(self.jp))
				gobi = str.join("|", gobi_dic[self.get_gobi(self.jp)])
				return "^({}(?:{}))(.*)$".format(gokan, gobi)
			case "上下"|"サ変":
				return "^({})(.*)$".format(self.remove_seps(self.remove_gobi(self.jp)))
			case "カ変": 
				return (
					"^(来る|来ない|来なく|来なかっ|来なければ|来なさ|来た|来て|"
					"来られ|来い|来よ)(.*)$"
				)
			case "形容": 
				gokan = self.remove_seps(self.remove_gobi(self.jp))
				gobi = [
					"い", "く", "かっ", "ければ", "がる", "がり", "がら", 
					"がれ", "がろ", "さ", "げ", "そう", "さそう", "すぎ", "過ぎ"
				]
				return "^({}(?:{}))(.*)$".format(gokan, str.join("|", gobi))
			case "英語": 
				word = str.join("", ["[{}{}]".format(c.lower(), c.upper()) for c in self.jp])
				return "^({})(.*)$".format(word)
			case _: 
				raise ValueError((
					"[Term.re_pattern] Term {} has invalid term_type. "
				).format(self))
			
	def __str__(self) -> str: 
		return (
			"Term(jp: {}, kana: {}, div0: {}, div1: {}, "
			"term_type: {}, priority: {})"
		).format(self.jp, self.kana, self.div0, self.div1, self.term_type, self.pri)
	
	def kahen_to_token(self, origin_str: str, div_type: Literal[0, 1, 2]) -> Tuple[List[str], List[str], List[str], str]: 
		kahen_dic = {
			"来る": "くる", "来ない": "こない", "来なく": "こなく", "来なかっ": "こなかっ", "来なければ": "こなければ", 
			"来なさ": "きなさい", "来た": "きた", "来て": "きて", "来られ": "こられ", "来い": "こい", "来よ": "こよ"
		}
		for key, value in kahen_dic.items(): 
			print("key: {}, value: {}".format(key, value))
			if origin_str.startswith(key): 
				return (
					["来", key[1:]], [value[0], value[1:]], ["0", "-1"], origin_str[len(key):]
				)
		raise ValueError((
			"[Term.kahen_to_token] The origin_str: {} does not match the jp part of this term: {}. "
		).format(origin_str, self.jp))
	
	def pre_to_token(self, origin_str: str, div_type: Literal[0, 1, 2]) -> Tuple[List[str], List[str], List[str], str]: 
		if self.term_type == "カ変": 
			return self.kahen_to_token(origin_str, div_type)
		div_char = ("/", "\\", "\\")[div_type]
		needless_div_char = ("\\", "/", "/")[div_type]
		div = [self.div0, self.div1, self.div1][div_type]
		jp = Term.div_remove(self.jp, needless_div_char)
		kana = Term.div_remove(self.kana, needless_div_char)
		division = Term.div_remove(div, needless_div_char)

		jp_gokan = self.remove_gobi(jp)
		kana_gokan = self.remove_gobi(kana)
		div_gokan = self.remove_gobi(division)

		if self.term_type == "英語": 
			letter_list = ["[{}{}]".format(c.lower(), c.upper()) for c in jp_gokan]
			pattern = "^({})(.*)$".format(str.join("", letter_list))
		elif self.term_type == "固有": 
			s = Term.remove_seps(jp_gokan)
			for dec_c in ("\\", "$", "(", ")", "*", "?", "+", ".", "[", "]", "{", "}", "|", "^"): 
				s = s.replace(dec_c, "\\{}".format(dec_c))
			pattern = "^({})(.*)$".format(s)
		else: 
			pattern = "^({})\\*?(.*)$".format(self.remove_seps(jp_gokan))
		result = re.match(pattern, origin_str)
		if result is None: 
			raise ValueError((
				"[Term.pre_to_token] The origin_str: {} does not match the jp part of this term: {}. "
			).format(origin_str, self.jp))
		leftover = result.group(2) 
		jp_list = Term.div_split(jp_gokan, div_char) if self.term_type != "英語" else Term.div_split(result.group(1), div_char)
		kana_list = Term.div_split(kana_gokan, div_char)
		div_list = Term.div_split(div_gokan, div_char)
		return (jp_list, kana_list, div_list, leftover)
	
	def to_token0(self, origin_str: str) -> List[Token0]: 
		jp_list, kana_list, div_list, leftover = self.pre_to_token(origin_str, 0)
		tokens = []

		for i in range(len(jp_list)): 
			if int(div_list[i]) in [0, 1, 2]: 
				tokens.append(Token0(
					Term.remove_seps(jp_list[i]), 
					Term.remove_seps(kana_list[i]), 
					int(div_list[i])
				))
			else: 
				tokens.append(Token0(Term.remove_seps(jp_list[i])))
		if len(leftover) > 0:
			tokens.append(Token0(Term.remove_seps(leftover)))
		return tokens
	
	def to_token1(self, origin_str: str) -> List[Token1]: 
		jp_list, kana_list, div_list, leftover = self.pre_to_token(origin_str, 1)

		tokens = []
		i = 0
		while i < len(jp_list): 
			if int(div_list[i]) == 0: 
				if i + 1 < len(jp_list) and int(div_list[i + 1]) == 0: 
					tokens.append(Token1(
						Term.remove_seps(jp_list[i] + jp_list[i + 1]), 
						Term.remove_seps(kana_list[i]), 
						Term.remove_seps(kana_list[i + 1])
					))
					i += 2
				else: 
					tokens.append(Token1(Term.remove_seps(jp_list[i]), Term.remove_seps(kana_list[i])))
					i += 1
			else: 
				tokens.append(Token1(Term.remove_seps(jp_list[i])))
				i += 1
		if len(leftover) > 0:
			tokens.append(Token1(Term.remove_seps(leftover)))
		return tokens
	
	def to_token2(self, origin_str: str) -> List[Token2]: 
		jp_list, kana_list, div_list, leftover = self.pre_to_token(origin_str, 2)

		tokens = []
		i = 0
		current_jp = ""
		current_kana = ""
		current_div = 0
		while i < len(jp_list): 
			if int(div_list[i]) != current_div: 
				if len(current_jp) != 0: 
					tokens.append(
						Token2(Term.remove_seps(current_jp), Term.remove_seps(current_kana)) 
						if current_div == 0 else Token2(Term.remove_seps(current_jp))
					)
				current_div = div_list[i]
				current_jp = jp_list[i]
				current_kana = kana_list[i]
				current_div = int(div_list[i])
			else: 
				current_jp += jp_list[i]
				current_kana += kana_list[i]
			i += 1
		if len(current_jp) != 0: 
			tokens.append(
				Token2(Term.remove_seps(current_jp), Term.remove_seps(current_kana)) 
				if current_div == 0 else Token2(Term.remove_seps(current_jp))
			)
		if len(leftover) > 0: 
			tokens.append(Token2(Term.remove_seps(leftover)))
		return tokens
	
	@classmethod
	def generate_insertions(cls, 
			origin_iter: Collection[str], fill_term: str, fill_count: int
		) -> Generator[List[str], None, None]: 
		m = len(origin_iter)
		total_len = m + fill_count

		for indices in itertools.combinations(range(total_len), fill_count): 
			result: List[str] = [""] * total_len
			indices_set = set(indices)
			for i in indices: 
				result[i] = fill_term
			original_iter = iter(origin_iter)
			for i in range(total_len): 
				if i not in indices_set: 
					result[i] = next(original_iter)
			yield result
			
	
	@classmethod
	def auto_divide(cls, 
			jp: str, kana: str, term_type: str
		) -> Optional[List[Tuple[str, str, str, str]]]: 
		# jp = "草臥れる", kana = "くたびれる", term_type = "上下"
		if len(jp) == 0 or len(kana) == 0: 
			return None
		if term_type not in ("英語", "固有") and not all(Term.is_jp_str(s) for s in (jp, kana)): 
			raise AutoDivisionDisabledError((
				"Unused character in Japanese found while the term_type is not \"固有\" or \"英語\". \n"
				"Auto division is disabled. "
			))
		if term_type == "五段": 
			gobi_list = ["う", "く", "ぐ", "す", "つ", "ぬ", "ぶ", "む", "る"]
			if jp[-1] != kana[-1] or jp[-1] not in gobi_list: 
				return None
			jp_list = [jp[:-1], jp[-1]]
			kana_list = [kana[:-1], kana[-1]]
		elif term_type == "上下": 
			if jp[-1] != kana[-1] or jp[-1] != "る": 
				return None
			jp_list = [jp[:-1], jp[-1]]
			kana_list = [kana[:-1], kana[-1]]
		elif term_type == "サ変":
			if jp[-2:] != kana[-2:] or jp[-2:] != "する": 
				return None
			jp_list = [jp[:-2], jp[-2:]]
			kana_list = [kana[:-2], kana[-2:]]
		elif term_type == "カ変":
			if jp != "来る" or kana != "くる": 
				return None
			return [("来る", "くる", "0", "0")]
		elif term_type == "形容":
			if jp[-1] != kana[-1] or jp[-1] != "い": 
				return None
			jp_list = [jp[:-1], jp[-1]]
			kana_list = [kana[:-1], kana[-1]]
		elif term_type == "名詞": 
			jp_list = [jp, None]
			kana_list = [kana, None]
		elif term_type == "固有": 
			if not all(Term.is_jp_str(s) for s in (jp, kana)): 
				raise AutoDivisionDisabledError((
					"Unused character in Japanese found while the term_type is \"固有\". \n"
					"Please manually divide the term. "
				))
			else: 
				jp_list = [jp, None]
				kana_list = [kana, None]
		elif term_type == "英語": 
			return [(jp, kana, "1", "0")]
		else: 
			return None
		
		# jp_list = ["草臥れ", "る"], kana_list = ["くたびれ", "る"]
		jp_gokan_list = []
		current_token = [jp_list[0][0], Term.is_kana(jp_list[0][0])]
		for c in jp_list[0][1:]: 
			if Term.is_kana(c) == current_token[1]: 
				current_token[0] += c
			else: 
				jp_gokan_list.append(current_token)
				current_token = [c, Term.is_kana(c)]
		jp_gokan_list.append(current_token)

		# jp_gokan_list = [["草臥", False], ["れ", True]]
		pattern_list = [
			("({})".format(gokan_token[0]) if gokan_token[1] else "(.+)") 
			for gokan_token in jp_gokan_list
		]
		pattern = "^{}$".format(str.join("", pattern_list))
		result = re.match(pattern, kana_list[0])
		if result is None: 
			return None
		if result.lastindex is None: 
			return None
		kana_gokan_list = [result.group(i) for i in range(1, result.lastindex + 1)]
		
		# kana_gokan_list = ["くたび", "れ"]
		part_list = []
		for i in range(len(jp_gokan_list)): 
			jp_gokan = jp_gokan_list[i][0]
			kana_gokan = kana_gokan_list[i]
			if jp_gokan_list[i][1]: 
				part_list.append([(jp_gokan, kana_gokan, "-1", "-1")])
			else: 
				choices = []
				repeat = min(len(jp_gokan) - 1, len(kana_gokan) - 1)
				if repeat == 0: 
					choices.append((jp_gokan, kana_gokan, "0", "0"))
				else: 
					for combo in itertools.product(["/", "/\\", ""], repeat=repeat): 
						if len(choices) >= 2000: 
							logging.warning((
								"[Term.auto_divide] To many possibilities. Please manually enter. "
							))
							raise AutoDivisionChoiceOverflowError(
								"[Term.auto_divide] Too many possibilities. \n"
								"Please manually enter divisions. "
							)
						div0_count = combo.count("/")
						div1_count = combo.count("/\\")
						if div1_count > 1: 
							continue
						jp_choice = str.join("", itertools.chain.from_iterable(
							itertools.zip_longest(jp_gokan, combo, fillvalue="")
						))
						if len(kana_gokan) - len(jp_gokan) < 0: 
							choices.append((jp_gokan, kana_gokan, "1", "0"))
							continue
						for kana_combo in Term.generate_insertions(
							combo, "", len(kana_gokan) - len(jp_gokan)
						): 
							kana_choice = str.join("", itertools.chain.from_iterable(
								itertools.zip_longest(kana_gokan, kana_combo, fillvalue="")
							))

							jp_div0 = jp_choice.replace("\\", "").split("/")
							kana_div0 = kana_choice.replace("\\", "").split("/")
							if len(jp_div0) != len(kana_div0): 
								logging.error((
									"[Term.auto_divide] Length of the following objects should be the same: \n"
									"jp_div0: {}, \nkana_div0: {}"
								).format(jp_div0, kana_div0))
								return []
							div0_list = []
							for i in range(len(jp_div0)): 
								if len(jp_div0[i]) == 1: 
									div0_list.append("0")
								elif len(kana_div0[i]) <= len(jp_div0[i]): 
									div0_list.append("2")
								else: 
									div0_list.append("1")
							div0_choice = str.join("/", div0_list)
							
							jp_div1 = jp_choice.replace("/", "").split("\\")
							kana_div1 = kana_choice.replace("/", "").split("\\")
							if len(jp_div1) != len(kana_div1):
								logging.warning((
									"[Term.auto_divide] Length of the following objects should be the same: \n"
									"jp_div1: {}, \nkana_div1: {}"
								).format(jp_div1, kana_div1))
							div1_list = ["0"] * len(jp_div1)
							div1_choice = str.join("\\", div1_list)
							choices.append((jp_choice, kana_choice, div0_choice, div1_choice))
				part_list.append(choices)
				
		part_list = [list(dict.fromkeys(part)) for part in part_list]
		# part_list = [
		# 	[('草/臥', 'くた/び', '0/0', '0'), ('草/臥', 'く/たび', '0/0', '0'), 
		# 	 ('草/\\臥', 'くた/\\び', '0/0', '0\\0'), ('草/\\臥', 'く/\\たび', '0/0', '0\\0'), 
		# 	 ('草臥', 'くたび', '2', '0')
		# 	], [('れ', 'れ', '-1', '-1')]
		#]

		result_list = []
		for combo in itertools.product(*part_list): 
			jp_result= str.join("/\\", [combo[i][0] for i in range(len(combo))])
			kana_result = str.join("/\\", [combo[i][1] for i in range(len(combo))])
			div0_result = str.join("/", [combo[i][2] for i in range(len(combo))])
			div1_result = str.join("\\", [combo[i][3] for i in range(len(combo))])
			if jp_list[1] is not None: 
				jp_result += "*{}".format(jp_list[1])
				kana_result += "*{}".format(kana_list[1])
				div0_result += "*-1"
				div1_result += "*-1"
			result_list.append((jp_result, kana_result, div0_result, div1_result))
		return result_list
	
	@classmethod
	def is_cjk_unified(cls, char: str) -> bool:
		"""判断是否为 CJK 统一汉字（含所有扩展区）"""
		if len(char) != 1: 
			raise ValueError((
				"[Term.is_cjk_unified]"
				"The length of input value char: {} is not 1. "
			).format(char))
		code = ord(char)
		return (
			0x4E00 <= code <= 0x9FFF or    # 基本区
			0x3400 <= code <= 0x4DBF or    # 扩展A
			0x20000 <= code <= 0x2A6DF or  # 扩展B
			0x2A700 <= code <= 0x2B73F or  # 扩展C
			0x2B740 <= code <= 0x2B81F or  # 扩展D
			0x2B820 <= code <= 0x2CEAF or  # 扩展E
			0x2CEB0 <= code <= 0x2EBEF or  # 扩展F
			0x30000 <= code <= 0x3134F or  # 扩展G
			0x31350 <= code <= 0x323AF or  # 扩展H
			0x2EBF0 <= code <= 0x2EE5F or  # 扩展I (Unicode 15.1+)
			code == 0x3005
		)
	
	@classmethod
	def is_alpha_num(cls, char: str) -> bool: 
		if len(char) != 1: 
			raise ValueError((
				"[Term.is_alpha_num]"
				"The length of input value char: {} is not 1. "
			).format(char))
		code = ord(char)
		return (
			0x41 <= code <= 0x5A or  # A-Z
			0x61 <= code <= 0x7A or  # a-z
			0x30 <= code <= 0x39    # 0-9
		)

class Dictionary: 

	PATTERNS = {
		"custom": re.compile("^\\(([^;\\)]+?);([^;\\)]+?);([^;\\)]+?);([^;\\)]+?)\\)(.*)"), 
		"priority": re.compile("^\\[(\\d+)\\](.*)")
	}

	def __init__(self, dic_path: str): 
		self.dic_path = dic_path
		self.dic: pd.DataFrame = self.load_from_csv(dic_path)
		self.index = self.dic.index.max() + 1 if len(self.dic) > 0 else 0

	def load_from_csv(self, csv_path: str) -> pd.DataFrame: 
		if not os.path.exists(csv_path):
			logging.warning((
				"[Dictionary.load_from_csv] The given csv_path: {} does not exist. "
				"An empty dictionary will be created. "
			).format(csv_path))
			new_df = pd.DataFrame(columns=["Japanese", "Kana", "Division0", "Division1", "Type", "Priority"])
			new_df.to_csv(csv_path, index=False)
			return new_df
		df = pd.read_csv(csv_path)
		new_df = self.check(df)
		return new_df
	
	def update(self, dic: pd.DataFrame) -> None: 
		new_df = self.check(dic)
		self.dic = new_df

	@classmethod
	def check(cls, df: pd.DataFrame) -> pd.DataFrame:
		new_df = df.copy()
		infos: List[str] = []
		columns = ["Japanese", "Kana", "Division0", "Division1", "Type", "Priority"]
		if not set(df.columns).issuperset(columns): 
			missing_columns = set(columns).difference(df.columns)
			mc_str = [str(mc) for mc in missing_columns]
			mc_joined = str.join(", ", mc_str) + ". "
			raise ValueError((
				"[Dictionary.load_from_csv] "
				"The dataframe loaded from given csv_path has this(these) column(s) missing: {}"
			).format(mc_joined))
		for idx, row in df.iterrows(): 
			try: 
				term = Term(
					row[columns[0]], row[columns[1]], row[columns[2]], 
					row[columns[3]], row[columns[4]], int(row[columns[5]])
				)
			except ValueError as ve: 
				infos.append((
					"[Dictionary.load_from_csv] "
					"Idx: {}, Row: {} is not valid. "
					"Error message: {}. "
				).format(idx, row, str(ve)))
				new_df.drop(idx, axis=0, inplace=True)
			except Exception as e: 
				logging.error("[Dictionary.load_from_csv] Unexpected exception happend. ")
				raise e
		for info in infos: 
			logging.warning(info)
		return new_df

	def get_df(self) -> pd.DataFrame: 
		return self.dic.copy()
	
	def get_term(self, index: int) -> Term: 
		if index not in self.dic.index: 
			raise ValueError((
				"[Dictionary.get_term] The index: {} is not in this dictionary. "
			).format(index))
		return Term(
			str(self.dic.at[index, "Japanese"]), str(self.dic.at[index, "Kana"]), 
			str(self.dic.at[index, "Division0"]), str(self.dic.at[index, "Division1"]), 
			str(self.dic.at[index, "Type"]), int(str(self.dic.at[index, "Priority"]))
		)
	
	def is_exists(self, term: Term) -> bool: 
		for _, row in self.dic.iterrows(): 
			if (term.jp == row["Japanese"] and term.kana == row["Kana"] and 
				term.div0 == row["Division0"] and term.div1 == row["Division1"] and 
				term.term_type == row["Type"] and term.pri == int(row["Priority"])
			): 
				return True
		return False
	
	def append(self, new_term: Term) -> Optional[int]: 
		if self.is_exists(new_term): 
			logging.warning((
				"[Dictionary.append] This term: {} already exists in this dictionary. "
			).format(new_term))
			return None
		self.dic.loc[self.index] = new_term.to_dict()
		self.index += 1
		return self.index - 1

	def remove(self, index: int) -> bool: 
		if index in self.dic.index:
			self.dic.drop(index, axis=0, inplace=True)
			return True
		return False

	def search_to_token0(self, line: str, priority: int) -> Tuple[bool, Optional[List[Token0]], str]: 
		init_char = line[0]
		filtered = self.dic[
			self.dic["Japanese"].str.lower().str.startswith(init_char.lower()) & 
			(self.dic["Priority"] == priority)
		]
		filtered["len_jp"] = filtered["Japanese"].apply(lambda x: len(Term.remove_seps(x)))
		filtered["len_jp_gokan"] = filtered["Japanese"].apply(lambda x: len(Term.remove_seps(Term.remove_gobi(x))))
		filtered.sort_values(by=["len_jp", "len_jp_gokan", "Priority"], ascending=[False, False, True], inplace=True)
		for _, row in filtered.iterrows(): 
			term = Term(
				row["Japanese"], row["Kana"], row["Division0"], 
				row["Division1"], row["Type"], int(row["Priority"])
			)
			pattern = term.re_pattern()
			result = re.match(pattern, line)
			if result is not None:
				return True, term.to_token0(result.group(1)), result.group(2)
		return False, None, line
	
	def search_to_token1(self, line: str, priority: int) -> Tuple[bool, Optional[List[Token1]], str]: 
		init_char = line[0]
		filtered = self.dic[
			self.dic["Japanese"].str.lower().str.startswith(init_char.lower()) & 
			(self.dic["Priority"] == priority)
		]
		filtered["len_jp"] = filtered["Japanese"].apply(lambda x: len(Term.remove_seps(x)))
		filtered["len_jp_gokan"] = filtered["Japanese"].apply(lambda x: len(Term.remove_seps(Term.remove_gobi(x))))
		filtered.sort_values(by=["len_jp", "len_jp_gokan", "Priority"], ascending=[False, False, True], inplace=True)
		for _, row in filtered.iterrows(): 
			term = Term(
				row["Japanese"], row["Kana"], row["Division0"], 
				row["Division1"], row["Type"], int(row["Priority"])
			)
			pattern = term.re_pattern()
			result = re.match(pattern, line)
			if result is not None:
				return True, term.to_token1(result.group(1)), result.group(2)
		return False, None, line

	def search_to_token2(self, line: str, priority: int) -> Tuple[bool, Optional[List[Token2]], str]: 
		init_char = line[0]
		filtered = self.dic[
			self.dic["Japanese"].str.lower().str.startswith(init_char.lower()) & 
			(self.dic["Priority"] == priority)
		]
		filtered["len_jp"] = filtered["Japanese"].apply(lambda x: len(Term.remove_seps(x)))
		filtered["len_jp_gokan"] = filtered["Japanese"].apply(lambda x: len(Term.remove_seps(Term.remove_gobi(x))))
		filtered.sort_values(by=["len_jp", "len_jp_gokan", "Priority"], ascending=[False, False, True], inplace=True)
		for _, row in filtered.iterrows(): 
			term = Term(
				row["Japanese"], row["Kana"], row["Division0"], 
				row["Division1"], row["Type"], int(row["Priority"])
			)
			pattern = term.re_pattern()
			result = re.match(pattern, line)
			if result is not None:
				return True, term.to_token2(result.group(1)), result.group(2)
		return False, None, line
	
	def line_to_tokens0(self, line: str) -> List[Token0]: 
		tokens = []
		remaining_line = line
		while len(remaining_line) > 0: 
			priority = 0
			custom_pattern = Dictionary.PATTERNS["custom"]
			priority_pattern = Dictionary.PATTERNS["priority"]
			custom_result = re.match(custom_pattern, remaining_line)
			priority_result = re.match(priority_pattern, remaining_line)
			if remaining_line[:2] in ["$$", "((", "))", "[[", "]]"]: 
				remaining_line = remaining_line[1:]
			elif custom_result is not None:	
				args = [custom_result.group(i) for i in range(1, 5)]
				remaining_line = custom_result.group(5)
				try: 
					term = Term(args[0], args[1], args[2], args[3], "固有", 0)
					tokens.extend(term.to_token0(Term.remove_seps(term.jp)))
					continue
				except: 
					pass
			elif priority_result is not None: 
				priority = int(priority_result.group(1))
				remaining_line = priority_result.group(2)
			elif remaining_line[0] == "$": 
				remaining_line = remaining_line[1:]
				while len(remaining_line) > 0 and remaining_line[0] != "$": 
					tokens.append(Token0(remaining_line[0]))
					remaining_line = remaining_line[1:]
				if len(remaining_line) > 0 and remaining_line[0] == "$": 
					remaining_line = remaining_line[1:]
				continue
			found, new_tokens, remaining_line = self.search_to_token0(remaining_line, priority)
			if found: 
				if new_tokens is not None: 
					tokens.extend(new_tokens)
			else: 
				tokens.append(Token0(remaining_line[0]))
				remaining_line = remaining_line[1:]
		return tokens
	
	def line_to_tokens1(self, line: str) -> List[Token1]: 
		tokens = []
		remaining_line = line
		while len(remaining_line) > 0: 
			priority = 0
			custom_pattern = Dictionary.PATTERNS["custom"]
			priority_pattern = Dictionary.PATTERNS["priority"]
			custom_result = re.match(custom_pattern, remaining_line)
			priority_result = re.match(priority_pattern, remaining_line)
			if remaining_line[:2] in ["$$", "((", "))", "[[", "]]"]: 
				remaining_line = remaining_line[1:]
			elif custom_result is not None:	
				args = [custom_result.group(i) for i in range(1, 5)]
				remaining_line = custom_result.group(5)
				try:
					term = Term(args[0], args[1], args[2], args[3], "固有", 0)
					tokens.extend(term.to_token1(Term.remove_seps(term.jp)))
					continue
				except:
					pass
			elif priority_result is not None: 
				priority = int(priority_result.group(1))
				remaining_line = priority_result.group(2)
			elif remaining_line[0] == "$": 
				remaining_line = remaining_line[1:]
				while len(remaining_line) > 0 and remaining_line[0] != "$": 
					tokens.append(Token1(remaining_line[0]))
					remaining_line = remaining_line[1:]
				if len(remaining_line) > 0 and remaining_line[0] == "$": 
					remaining_line = remaining_line[1:]
				continue
			found, new_tokens, remaining_line = self.search_to_token1(remaining_line, priority)
			if found: 
				if new_tokens is not None: 
					tokens.extend(new_tokens)
			else: 
				tokens.append(Token1(remaining_line[0]))
				remaining_line = remaining_line[1:]
		return tokens 
	
	def line_to_tokens2(self, line: str) -> List[Token2]:
		tokens = []
		remaining_line = line
		while len(remaining_line) > 0: 
			priority = 0
			custom_pattern = Dictionary.PATTERNS["custom"]
			priority_pattern = Dictionary.PATTERNS["priority"]
			custom_result = re.match(custom_pattern, remaining_line)
			priority_result = re.match(priority_pattern, remaining_line)
			if remaining_line[:2] in ["$$", "((", "))", "[[", "]]"]: 
				remaining_line = remaining_line[1:]
			elif custom_result is not None:	
				args = [custom_result.group(i) for i in range(1, 5)]
				remaining_line = custom_result.group(5)
				try: 
					term = Term(args[0], args[1], args[2], args[3], "固有", 0)
					tokens.extend(term.to_token2(Term.remove_seps(term.jp)))
					continue
				except Exception as e: 
					logging.warning((
						"[Dictionary.line_to_token2] "
						"Exception happened when processing args: {}. "
					).format(args))
			elif priority_result is not None: 
				priority = int(priority_result.group(1))
				remaining_line = priority_result.group(2)
			elif remaining_line[0] == "$": 
				remaining_line = remaining_line[1:]
				while len(remaining_line) > 0 and remaining_line[0] != "$": 
					tokens.append(Token2(remaining_line[0], None, True))
					remaining_line = remaining_line[1:]
				if len(remaining_line) > 0 and remaining_line[0] == "$": 
					remaining_line = remaining_line[1:]
				continue
			found, new_tokens, remaining_line = self.search_to_token2(remaining_line, priority)
			if found: 
				if new_tokens is not None:
					tokens.extend(new_tokens)
			else: 
				tokens.append(Token2(remaining_line[0]))
				remaining_line = remaining_line[1:]
		return tokens 

	def __len__(self) -> int: 
		return len(self.dic)
	
	def find(self, part: str) -> "Dictionary": 
		result_df = self.dic.copy()
		result_df["in_jp_no_seps"] = result_df["Japanese"].apply(
			lambda x: part in Term.remove_seps(x)
		)
		result_df["in_kana_no_seps"] = result_df["Kana"].apply(
			lambda x: part in Term.remove_seps(x)
		)
		result_df = result_df[result_df["in_jp_no_seps"] | result_df["in_kana_no_seps"]]
		result_df.drop(["in_jp_no_seps", "in_kana_no_seps"], axis=1, inplace=True)
		new_dic = Dictionary(self.dic_path)
		new_dic.update(result_df)
		return new_dic
	
	def copy(self) -> "Dictionary": 
		new_dic = Dictionary(self.dic_path)
		new_dic.update(self.dic)
		return new_dic
	
	def save(self) -> None: 
		self.dic.to_csv(self.dic_path, index=False)



if __name__ == "__main__": 

	import platform
	from pathlib import Path

	def get_config_dir(app_name: str) -> Path: 
		if platform.system() == "Windows": 
			return Path.home() / "AppData" / "Roaming" / app_name
		elif platform.system() == "Darwin": 
			return Path.home() / "Library" / "Application Support" / app_name
		else: 
			return Path.home() / ".config" / app_name
		
	logging.basicConfig(
		level=logging.DEBUG, 
		format="[%(asctime)s] %(levelname)s: %(message)s", 
		datefmt="%Y-%m-%d %H:%M:%S"
	)
	DIRPATH = get_config_dir("FuriganaAssistant")

	text = "$歌$：初音ミク　$曲$：DECO*27"

	dic = Dictionary(str(DIRPATH / "dic.csv"))
	token_list = dic.line_to_tokens2(text)
	for token in token_list: 
		print(token.jp, token.kana)