#!/usr/bin/python

import sys

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def arbitrage(factors):
    result = []
    for i in range(len(factors)):
        result.append(1 / factors[i])
    total = sum(result)
    for i in range(len(result)):
        result[i] /= total
    return result

def show_result(factors, result, value = 1):
    valued = result.copy()
    for i in range(len(valued)):
        valued[i] *= value
    print(valued)
    print(str((result[0] * factors[0] - 1) * 100) + "%")

class Combiner:
    def __init__(self):
        self.best_index = []
        self.best = []
        self.factors = {}

    def update_best(self):
        for identifier, factors in self.factors.items():
            if self.best:
                for i in range(len(self.best)):
                    if factors[i] > self.best[i]:
                        self.best[i] = factors[i]
                        self.best_index[i] = identifier
            else:
                self.best = factors
                self.best_index = [identifier] * len(factors)

    def add(self, identifier, factors, show = False):
        self.factors[identifier] = factors
        self.update_best()
        if show:
            show_result(factors, arbitrage(factors))

    def show(self, value = 1):
        if self.best:
            print(self.best_index)
            result = arbitrage(self.best)
            show_result(self.best, result, value)

#if len(sys.argv) > 1:
#    value = float(sys.argv[1])
#else:
#    value = 1
#combiner = Combiner()
#while True:
#    try:
#        line = input(str(combiner.n) + ": ")
#    except EOFError:
#        combiner.show(value)
#        quit()
#    odds = line.split(" ")
#    factors = []
#    for odd in odds:
#        components = odd.split("/")
#        if len(components) == 1:
#            factor = float(components[0])
#        else:
#            factor = 1 + float(components[0]) / float(components[1])
#        factors.append(factor)
#    combiner.add(factors, True)

combiners = {}
options = Options()
driver = webdriver.Chrome(options=options)
identifier = "betfair"
driver.get("https://www.betfair.com/sport/football")
items = driver.find_elements_by_class_name("event-information")
for item in items:
    names = item.find_elements_by_class_name("team-name")
    key = tuple(names)
    if key in combiners:
        combiner = combiners[key]
    for name in names:
        print(name.text)
    fields = item.find_elements_by_class_name("ui-runner-price")
    skip = len(fields) - 3
    fields = fields[skip:skip + 3]
    prices = []
    combiner = Combiner()
    factors = []
    for field in fields:
        price = field.text.strip()
        prices.append(price)
        if price != "":
            if price == "EVS":
                factor = 2
            else:
                components = price.split("/")
                factor = 1 + float(components[0]) / float(components[1])
            factors.append(factor)
    print(prices)
    combiner.add(identifier, factors, True)
