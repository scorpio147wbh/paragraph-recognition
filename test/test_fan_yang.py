#!/usr/bin/env python
# coding: utf-8
import os
from unittest import TestCase
from mock import Mock
from method import FanYang, AnalyzedSentence, configure, get_method


class TestFanYang(TestCase):
    method_config = {
        'essentials': {
            'third_person_pronoun': 'data/third-person-pronoun.txt',
            'demonstrative_pronoun': 'data/demonstrative-pronoun.txt',
            'cue_word': 'data/cue-word.txt',
            'stop_word': 'data/stop-word.txt'
        },
        'word_similarity_calculators': {
            'how_net': {
                'class': 'HowNetCalculator',
                'sememe_tree_file': 'data/whole.dat',
                'glossary_file': 'data/glossary.dat'
            }
        },
        'sentence_similarity_calculator': {
            'ssc_with_how_net': {
                'word_similarity_calculator': 'how_net',
                'cache_filename': 'data/sentence-score.cache'
            }
        },
        'method': {
            'fan_yang': {
                'class': 'FanYang',
                'sentence_similarity_calculator': 'ssc_with_how_net',
                'train_data_filename': 'data/train-set.txt',
                'classifier_filename': 'data/fan-yang.classifier'
            }
        }
    }

    def test_train(self):
        mock_fan_yang = Mock(FanYang)
        mock_fan_yang.train_data_filename = 'data/train-set.txt'
        mock_fan_yang.feature_names = FanYang.feature_names
        mock_fan_yang.classifier = None
        mock_fan_yang.train = FanYang.train.__get__(mock_fan_yang)
        mock_fan_yang.train()
        self.assertIsNotNone(mock_fan_yang.classifier)

    def test_is_follow_up(self):
        configure(self.method_config)
        fan_yang = get_method('fan_yang')
        question = AnalyzedSentence(u'003ded97d09a05a4b7a48de0737934f0',
                                    u'[[[{"cont": "我", "parent": 1, "relate": "SBV", "ne": "O", "pos": "r", "arg": [], "id": 0}, {"cont": "看", "parent": 5, "relate": "ADV", "ne": "O", "pos": "v", "arg": [{"end": 0, "type": "A0", "id": 0, "beg": 0}, {"end": 2, "type": "A1", "id": 1, "beg": 2}], "id": 1}, {"cont": "京", "parent": 1, "relate": "VOB", "ne": "S-Ns", "pos": "j", "arg": [], "id": 2}, {"cont": "东", "parent": 4, "relate": "ATT", "ne": "O", "pos": "nd", "arg": [], "id": 3}, {"cont": "商城", "parent": 5, "relate": "SBV", "ne": "O", "pos": "n", "arg": [], "id": 4}, {"cont": "只有", "parent": -1, "relate": "HED", "ne": "O", "pos": "c", "arg": [{"end": 4, "type": "A0", "id": 0, "beg": 3}, {"end": 8, "type": "A1", "id": 1, "beg": 6}], "id": 5}, {"cont": "圣宝", "parent": 8, "relate": "ATT", "ne": "O", "pos": "n", "arg": [], "id": 6}, {"cont": "SV", "parent": 6, "relate": "VOB", "ne": "O", "pos": "ws", "arg": [], "id": 7}, {"cont": "922", "parent": 5, "relate": "VOB", "ne": "O", "pos": "m", "arg": [], "id": 8}, {"cont": "，", "parent": 5, "relate": "WP", "ne": "O", "pos": "wp", "arg": [], "id": 9}, {"cont": "没有", "parent": 5, "relate": "COO", "ne": "O", "pos": "v", "arg": [{"end": 21, "type": "A0", "id": 0, "beg": 11}], "id": 10}, {"cont": "927.", "parent": 13, "relate": "ADV", "ne": "O", "pos": "m", "arg": [], "id": 11}, {"cont": "我", "parent": 13, "relate": "SBV", "ne": "O", "pos": "r", "arg": [], "id": 12}, {"cont": "上网", "parent": 21, "relate": "ATT", "ne": "O", "pos": "v", "arg": [], "id": 13}, {"cont": "查", "parent": 13, "relate": "COO", "ne": "O", "pos": "v", "arg": [{"end": 12, "type": "A0", "id": 0, "beg": 12}], "id": 14}, {"cont": "说", "parent": 14, "relate": "COO", "ne": "O", "pos": "v", "arg": [{"end": 18, "type": "A1", "id": 0, "beg": 16}], "id": 15}, {"cont": "927", "parent": 17, "relate": "SBV", "ne": "O", "pos": "m", "arg": [], "id": 16}, {"cont": "是", "parent": 15, "relate": "VOB", "ne": "O", "pos": "v", "arg": [{"end": 16, "type": "A0", "id": 0, "beg": 16}, {"end": 18, "type": "A1", "id": 1, "beg": 18}], "id": 17}, {"cont": "922", "parent": 17, "relate": "VOB", "ne": "O", "pos": "m", "arg": [], "id": 18}, {"cont": "的", "parent": 13, "relate": "RAD", "ne": "O", "pos": "u", "arg": [], "id": 19}, {"cont": "升级", "parent": 21, "relate": "ATT", "ne": "O", "pos": "v", "arg": [], "id": 20}, {"cont": "版", "parent": 10, "relate": "VOB", "ne": "O", "pos": "n", "arg": [], "id": 21}, {"cont": "，", "parent": 10, "relate": "WP", "ne": "O", "pos": "wp", "arg": [], "id": 22}, {"cont": "在", "parent": 26, "relate": "ADV", "ne": "O", "pos": "p", "arg": [], "id": 23}, {"cont": "哪里", "parent": 23, "relate": "POB", "ne": "O", "pos": "r", "arg": [], "id": 24}, {"cont": "能", "parent": 26, "relate": "ADV", "ne": "O", "pos": "v", "arg": [], "id": 25}, {"cont": "买", "parent": 10, "relate": "COO", "ne": "O", "pos": "v", "arg": [{"end": 24, "type": "LOC", "id": 0, "beg": 23}], "id": 26}, {"cont": "到", "parent": 26, "relate": "CMP", "ne": "O", "pos": "v", "arg": [], "id": 27}, {"cont": "啊", "parent": 26, "relate": "RAD", "ne": "O", "pos": "u", "arg": [], "id": 28}, {"cont": "，", "parent": 26, "relate": "WP", "ne": "O", "pos": "wp", "arg": [], "id": 29}, {"cont": "要", "parent": 32, "relate": "ADV", "ne": "O", "pos": "v", "arg": [], "id": 30}, {"cont": "能", "parent": 32, "relate": "ADV", "ne": "O", "pos": "v", "arg": [], "id": 31}, {"cont": "保证", "parent": 26, "relate": "COO", "ne": "O", "pos": "v", "arg": [{"end": 33, "type": "A1", "id": 0, "beg": 33}], "id": 32}, {"cont": "质量", "parent": 32, "relate": "VOB", "ne": "O", "pos": "n", "arg": [], "id": 33}, {"cont": "的", "parent": 32, "relate": "RAD", "ne": "O", "pos": "u", "arg": [], "id": 34}, {"cont": "，", "parent": 26, "relate": "WP", "ne": "O", "pos": "wp", "arg": [], "id": 35}, {"cont": "还有", "parent": 26, "relate": "COO", "ne": "O", "pos": "v", "arg": [], "id": 36}, {"cont": "你", "parent": 36, "relate": "DBL", "ne": "O", "pos": "r", "arg": [], "id": 37}, {"cont": "说", "parent": 36, "relate": "COO", "ne": "O", "pos": "v", "arg": [], "id": 38}, {"cont": "那", "parent": 40, "relate": "ATT", "ne": "O", "pos": "r", "arg": [], "id": 39}, {"cont": "非同凡响", "parent": 45, "relate": "ADV", "ne": "O", "pos": "i", "arg": [], "id": 40}, {"cont": "608", "parent": 45, "relate": "ADV", "ne": "O", "pos": "m", "arg": [], "id": 41}, {"cont": "在", "parent": 45, "relate": "ADV", "ne": "O", "pos": "p", "arg": [], "id": 42}, {"cont": "哪里", "parent": 42, "relate": "POB", "ne": "O", "pos": "r", "arg": [], "id": 43}, {"cont": "能", "parent": 45, "relate": "ADV", "ne": "O", "pos": "v", "arg": [], "id": 44}, {"cont": "买", "parent": 38, "relate": "VOB", "ne": "O", "pos": "v", "arg": [{"end": 43, "type": "LOC", "id": 0, "beg": 42}], "id": 45}, {"cont": "到", "parent": 45, "relate": "CMP", "ne": "O", "pos": "v", "arg": [], "id": 46}, {"cont": "呢", "parent": 45, "relate": "RAD", "ne": "O", "pos": "u", "arg": [], "id": 47}, {"cont": "？", "parent": 38, "relate": "WP", "ne": "O", "pos": "wp", "arg": [], "id": 48}], [{"cont": "想", "parent": -1, "relate": "HED", "ne": "O", "pos": "v", "arg": [], "id": 0}, {"cont": "在", "parent": 5, "relate": "ADV", "ne": "O", "pos": "p", "arg": [], "id": 1}, {"cont": "这", "parent": 4, "relate": "ATT", "ne": "O", "pos": "r", "arg": [], "id": 2}, {"cont": "两", "parent": 4, "relate": "ATT", "ne": "O", "pos": "m", "arg": [], "id": 3}, {"cont": "个", "parent": 1, "relate": "POB", "ne": "O", "pos": "q", "arg": [], "id": 4}, {"cont": "中选", "parent": 0, "relate": "VOB", "ne": "O", "pos": "v", "arg": [{"end": 4, "type": "LOC", "id": 0, "beg": 1}, {"end": 6, "type": "A1", "id": 1, "beg": 6}], "id": 5}, {"cont": "一个", "parent": 5, "relate": "VOB", "ne": "O", "pos": "m", "arg": [], "id": 6}]]]')
        result = fan_yang.is_follow_up(question, None, None)
        self.assertTrue(result)

    def test_save_classifier(self):
        mock_fan_yang = Mock(FanYang)
        mock_fan_yang.classifier_filename = 'data/test-fan-yang.classifier'
        mock_fan_yang.classifier = 'test'
        mock_fan_yang.save_classifier = FanYang.save_classifier.__get__(mock_fan_yang)
        mock_fan_yang.save_classifier()
        self.assertTrue(os.path.isfile(mock_fan_yang.classifier_filename))
        os.remove(mock_fan_yang.classifier_filename)

    def test_load_classifier(self):
        mock_fan_yang = Mock(FanYang)
        mock_fan_yang.classifier_filename = 'data/fan-yang.classifier'
        mock_fan_yang.classifier = None
        mock_fan_yang.load_classifier = FanYang.load_classifier.__get__(mock_fan_yang)
        FanYang.load_classifier(mock_fan_yang)
        self.assertIsNotNone(mock_fan_yang.classifier)
