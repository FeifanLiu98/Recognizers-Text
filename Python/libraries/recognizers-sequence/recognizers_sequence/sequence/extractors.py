from abc import ABC, abstractmethod
from typing import List, Dict, Set, Pattern, Match
from collections import namedtuple
import regex as re
from recognizers_sequence.sequence.config.url_configuration import URLConfiguration
from .constants import *
from recognizers_text.utilities import RegExpUtility
from recognizers_text.extractor import Extractor, ExtractResult
from recognizers_number.culture import CultureInfo
from recognizers_sequence.resources import *
from urllib.parse import urlparse
from os.path import splitext

ReVal = namedtuple('ReVal', ['re', 'val'])
MatchesVal = namedtuple('MatchesVal', ['matches', 'val'])


class SequenceExtractor(Extractor):
    @property
    @abstractmethod
    def regexes(self) -> List[ReVal]:
        raise NotImplementedError

    @property
    @abstractmethod
    def _extract_type(self) -> str:
        raise NotImplementedError

    def extract(self, source: str) -> List[ExtractResult]:
        result: List[ExtractResult] = list()
        if not self._pre_check_str(source):
            return result

        matched: List[bool] = [False] * len(source)

        match_source: Dict[Match, str] = dict()

        matches_list = list(
            map(lambda x: MatchesVal(matches=list(re.finditer(x.re, source)), val=x.val), self.regexes))
        matches_list = list(filter(lambda x: len(x.matches) > 0, matches_list))

        for ml in matches_list:
            for m in ml.matches:
                if self._is_valid_match(m):
                    for j in range(len(m.group())):
                        matched[m.start() + j] = True
                    # Keep Source Data for extra information
                    match_source[m] = ml.val
        last = -1

        for i in range(len(source)):
            if not matched[i]:
                last = i
            else:
                if i + 1 == len(source) or not matched[i + 1]:
                    start = last + 1
                    length = i - last
                    substring = source[start:start + length].strip()
                    src_match = next(
                        (x for x in iter(match_source) if (x.start() ==
                                                           start and (x.end() - x.start()) == length)),
                        None)

                    if src_match is not None:
                        value = ExtractResult()
                        value.start = start
                        value.length = length
                        value.text = substring
                        value.type = self._extract_type
                        value.data = match_source.get(src_match, None)
                        result.append(value)

        return result

    @staticmethod
    def _pre_check_str(source: str) -> bool:
        return len(source) != 0

    def _is_valid_match(self, source: str) -> bool:
        return True


class BasePhoneNumberExtractor(SequenceExtractor):

    def __init__(self, config):
        self.config = config
        word_boundaries_regex = config.word_boundaries_regex
        non_word_boundaries_regex = config.non_word_boundaries_regex
        end_word_boundaries_regex = config.end_word_boundaries_regex

        self._regexes = [
            ReVal(RegExpUtility.get_safe_reg_exp(BasePhoneNumbers.GeneralPhoneNumberRegex(
                word_boundaries_regex, end_word_boundaries_regex)), Constants.PHONE_NUMBER_REGEX_GENERAL),
            ReVal(RegExpUtility.get_safe_reg_exp(BasePhoneNumbers.BRPhoneNumberRegex(
                word_boundaries_regex, non_word_boundaries_regex, end_word_boundaries_regex)),
                Constants.PHONE_NUMBER_REGEX_BR),
            ReVal(RegExpUtility.get_safe_reg_exp(BasePhoneNumbers.UKPhoneNumberRegex(
                word_boundaries_regex, non_word_boundaries_regex, end_word_boundaries_regex)),
                Constants.PHONE_NUMBER_REGEX_UK),
            ReVal(RegExpUtility.get_safe_reg_exp(BasePhoneNumbers.DEPhoneNumberRegex(
                word_boundaries_regex, end_word_boundaries_regex)), Constants.PHONE_NUMBER_REGEX_DE),
            ReVal(RegExpUtility.get_safe_reg_exp(BasePhoneNumbers.USPhoneNumberRegex(
                word_boundaries_regex, non_word_boundaries_regex, end_word_boundaries_regex)),
                Constants.PHONE_NUMBER_REGEX_US),
            ReVal(RegExpUtility.get_safe_reg_exp(BasePhoneNumbers.CNPhoneNumberRegex(
                word_boundaries_regex, end_word_boundaries_regex)), Constants.PHONE_NUMBER_REGEX_CN),
            ReVal(RegExpUtility.get_safe_reg_exp(BasePhoneNumbers.DKPhoneNumberRegex(
                word_boundaries_regex, end_word_boundaries_regex)), Constants.PHONE_NUMBER_REGEX_DK),
            ReVal(RegExpUtility.get_safe_reg_exp(BasePhoneNumbers.ITPhoneNumberRegex(
                word_boundaries_regex, end_word_boundaries_regex)), Constants.PHONE_NUMBER_REGEX_IT),
            ReVal(RegExpUtility.get_safe_reg_exp(BasePhoneNumbers.NLPhoneNumberRegex(
                word_boundaries_regex, end_word_boundaries_regex)), Constants.PHONE_NUMBER_REGEX_NL),
            ReVal(RegExpUtility.get_safe_reg_exp(BasePhoneNumbers.SpecialPhoneNumberRegex(
                word_boundaries_regex, end_word_boundaries_regex)), Constants.PHONE_NUMBER_REGEX_SPECIAL),
        ]

    @property
    def regexes(self) -> List[ReVal]:
        return self._regexes

    @property
    def _extract_type(self) -> str:
        return Constants.SYS_PHONE_NUMBER

    def extract(self, source: str):
        extract_results = super().extract(source)
        ret = []
        format_indicator_regex = re.compile(
            BasePhoneNumbers.FormatIndicatorRegex, re.IGNORECASE | re.DOTALL)
        for er in extract_results:
            ch = source[er.start - 1]
            if er.start == 0 or ch not in BasePhoneNumbers.BoundaryMarkers:
                ret.append(er)
            elif ch in BasePhoneNumbers.SpecialBoundaryMarkers and \
                    format_indicator_regex.search(er.text) and \
                    er.start >= 2:
                ch_gap = source[er.start - 2]
                if not ch_gap.isdigit():
                    ret.append(er)
                front = source[0:er.start - 1]
                international_dialing_prefix_regex = re.compile(
                    BasePhoneNumbers.InternationDialingPrefixRegex)
                match = international_dialing_prefix_regex.search(front)
                if match is not None:
                    er.start = match.start()
                    er.length = er.length + match.end() - match.start() + 1
                    er.text = source[er.start:er.start + er.length].strip()
                    ret.append(er)

        # filter hexadecimal address like 00 10 00 31 46 D9 E9 11
        for m in re.finditer(BasePhoneNumbers.PhoneNumberMaskRegex, source):
            ret = [er for er in ret if er.start <
                   m.start() or er.end > m.end()]

        return ret


class BaseEmailExtractor(SequenceExtractor):
    @property
    def _extract_type(self) -> str:
        return Constants.SYS_EMAIL

    @property
    def regexes(self) -> List[ReVal]:
        return self._regexes

    def __init__(self):
        self._regexes = [
            ReVal(RegExpUtility.get_safe_reg_exp(
                BaseEmail.EmailRegex), Constants.EMAIL_REGEX),
            # EmailRegex2 will break the code as it's not supported in Python, comment out for now
            # ReVal(RegExpUtility.get_safe_reg_exp(BaseEmail.EmailRegex2, remove_question=True), Constants.EMAIL_REGEX),
        ]


class BaseHashTagExtractor(SequenceExtractor):
    @property
    def _extract_type(self) -> str:
        return Constants.SYS_HASHTAG

    @property
    def regexes(self) -> List[ReVal]:
        return self._regexes

    def __init__(self):
        self._regexes = [ReVal(RegExpUtility.get_safe_reg_exp(BaseHashtag.HashtagRegex), Constants.HASHTAG_REGEX)]


class BaseGUIDExtractor(SequenceExtractor):
    @property
    def _extract_type(self) -> str:
        return Constants.SYS_GUID

    @property
    def regexes(self) -> List[ReVal]:
        return self._regexes

    def __init__(self):
        self._regexes = [ReVal(RegExpUtility.get_safe_reg_exp(BaseGUID.GUIDRegex), Constants.GUID_REGEX)]


class BaseIpExtractor(SequenceExtractor):
    @property
    def _extract_type(self) -> str:
        return Constants.SYS_IP

    @property
    def regexes(self) -> List[ReVal]:
        return self._regexes

    def extract(self, source: str) -> List[ExtractResult]:
        result: List[ExtractResult] = list()
        if not self._pre_check_str(source):
            return result

        matched: List[bool] = [False] * len(source)

        match_source: Dict[Match, str] = dict()
        matches_list = list(
            map(lambda x: MatchesVal(matches=list(re.finditer(x.re, source)), val=x.val), self.regexes))
        matches_list = list(filter(lambda x: len(x.matches) > 0, matches_list))

        for ml in matches_list:
            for m in ml.matches:
                for j in range(len(m.group())):
                    matched[m.start() + j] = True
                # Keep Source Data for extra information
                match_source[m] = ml.val
        last = -1

        for i in range(len(source)):
            if not matched[i]:
                last = i
            else:
                if i + 1 == len(source) or not matched[i + 1]:
                    start = last + 1
                    length = i - last
                    substring = source[start:start + length].strip()

                    if substring.startswith(Constants.IPV6_ELLIPSIS) and (
                            start > 0 and (str.isdigit(source[start - 1]) or
                                           str.isalpha(source[start - 1]))):
                        continue

                    elif substring.endswith(Constants.IPV6_ELLIPSIS) and (
                            i + 1 < len(source) and (str.isdigit(source[i + 1]) or
                                                     str.isalpha(source[i + 1]))):
                        continue

                    src_match = next(
                        (x for x in iter(match_source) if (x.start() ==
                                                           start and (x.end() - x.start()) == length)),
                        None)

                    if src_match is not None:
                        value = ExtractResult()
                        value.start = start
                        value.length = length
                        value.text = substring
                        value.type = self._extract_type
                        value.data = match_source.get(src_match, None)
                        result.append(value)
        return result

    def __init__(self):
        self._regexes = [
            ReVal(RegExpUtility.get_safe_reg_exp(BaseIp.Ipv4Regex), Constants.IP_REGEX_IPV4),
            ReVal(RegExpUtility.get_safe_reg_exp(BaseIp.Ipv6Regex), Constants.IP_REGEX_IPV6)
        ]


class BaseMentionExtractor(SequenceExtractor):
    @property
    def _extract_type(self) -> str:
        return Constants.SYS_MENTION

    @property
    def regexes(self) -> List[ReVal]:
        return self._regexes

    def __init__(self):
        self._regexes = [ReVal(RegExpUtility.get_safe_reg_exp(BaseMention.MentionRegex), Constants.MENTION_REGEX)]


class BaseURLExtractor(SequenceExtractor):
    @property
    def _extract_type(self) -> str:
        return Constants.SYS_URL

    @property
    def ambiguous_time_term(self) -> ReVal:
        return self._ambiguous_time_term

    @property
    def config(self) -> URLConfiguration:
        return self._config

    @config.setter
    def config(self, config):
        self._config = config

    def _is_valid_match(self, match: Match) -> bool:
        # For cases like "7.am" or "8.pm" which are more likely time terms.
        return re.match(self.ambiguous_time_term.re, match.group(0)) is None

    @property
    def regexes(self) -> List[ReVal]:
        return self._regexes

    @ambiguous_time_term.setter
    def ambiguous_time_term(self, value):
        self._ambiguous_time_term = value

    def __init__(self, config):
        self.config = config

        self._regexes = [
            ReVal(config.ip_url_regex, Constants.URL_REGEX),
            ReVal(config.url_regex, Constants.URL_REGEX),
            ReVal(RegExpUtility.get_safe_reg_exp(BaseURL.UrlRegex2), Constants.URL_REGEX)
        ]

        self._ambiguous_time_term = ReVal(RegExpUtility.get_safe_reg_exp(BaseURL.AmbiguousTimeTerm),
                                          Constants.URL_REGEX)
