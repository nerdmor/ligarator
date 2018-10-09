import re
import os
import json
from liga_functions import *
from pprint import pprint
from ortools.linear_solver import pywraplp
from random import randint, shuffle
import tkinter as tk
from tkinter import filedialog
import sys

# SETUP
SHIPPING = float(input('Qual o valor a ser considerado de frete?(Formato: xx.yy):\n'))
clear_screen()

print('Na janela a seguir selecione o arquivo que contem a sua want.')
print('As cartas precisam estar uma por linha.')
print('No seguinte formato: [N] [cardname]')
print('Ex: 4 Guard Gomazoa')
input('Pressione enter para abrir a janela')
clear_screen()

root = tk.Tk()
root.withdraw()
FILENAME = filedialog.askopenfilename()

# GET WANTLIST
with open(FILENAME, 'r', encoding='utf-8') as f:
    wantlist_raw = f.readlines()
    shuffle(wantlist_raw)

# Parse wantlist
rex = re.compile('^(\\d+)?[\\s\\*]*(.+)')
wantlist = []
for line in wantlist_raw:
    matches = rex.findall(line)
    if matches:
        match = matches[0]
        item = {'card': match[1].lower()}
        if match[0]:
            item['quantity'] = int(match[0])
        else:
            item['quantity'] = 1
        wantlist.append(item)
    else:
        print('Carta mal formatada:')
        print('\t' + line)
        sysexit()

# get offers
offers = []
BASE_URL = 'https://www.ligamagic.com.br/_mobile_lm/ajax/search.php'
for wish in wantlist:
    print('Pegando ofertas para ' + wish['card'])
    new_offers = get_liga_offers(BASE_URL, wish['card'])
    if len(new_offers) < 1:
        print('\tCarta nao encontrada. Verifique o nome.')
        sysexit()
    print('\ttemos {} ofertas!'.format(len(new_offers)))
    offers += new_offers
    sleeptime = randint(5, 25)
    print('\tdormindo por {} segundos'.format(sleeptime))
    time.sleep(sleeptime)

# get card offers per store
storenames = set([o['store'] for o in offers])
cardnames = set([w['card'] for w in wantlist])
stores = []
for sname in storenames:
    store = {
        'name': sname,
        'shipping': SHIPPING,
        'offers': []
    }
    for card in cardnames:
        store_wish = {
            'card': card,
            'price': 0.0,
            'stock': 0}
        for offer in offers:
            if offer['store'] == sname and offer['card'] == card:
                store_wish['price'] = offer['price']
                store_wish['stock'] = offer['quantity']
                break
        store['offers'].append(store_wish)
    stores.append(store)


# instantiate solver
solver = pywraplp.Solver(
    'SolveIntegerProblem', pywraplp.Solver.CBC_MIXED_INTEGER_PROGRAMMING)


# Prepare variables
variables = []
for s in stores:
    for o in s['offers']:
        varname = s['name'][:31] + '|' + o['card'][:32]
        numvar = solver.IntVar(0.0, o['stock'], varname)
        variables.append(numvar)

# Shipping as variables
for s in stores:
    varname = s['name'][:31] + '|frete'
    numvar = solver.IntVar(0.0, 1.0, varname)
    variables.append(numvar)

# objective: minimize the total value
objective = solver.Objective()
i = -1
for s in stores:
    for o in s['offers']:
        i += 1
        objective.SetCoefficient(variables[i], o['price'])

for s in stores:
    i += 1
    objective.SetCoefficient(variables[i], s['shipping'])
objective.SetMinimization()

# constraint: must buy all cards
constraints = []
for card in cardnames:
    # how many of that card we want to buy?
    wanted_quantity = 0
    for w in wantlist:
        if w['card'] == card:
            wanted_quantity = w['quantity']
            break
    print('we want {} of {}'.format(wanted_quantity, card))

    constraints.append(
        solver.Constraint(wanted_quantity, wanted_quantity)
    )
    c = len(constraints) - 1

    card_partial_name = '|' + card[:32]
    for i in range(len(variables)):
        if card_partial_name in variables[i].name():
            constraints[c].SetCoefficient(variables[i], 1)
        else:
            constraints[c].SetCoefficient(variables[i], 0)

# constraint: must buy shipping for each store
for store in storenames:
    constraints.append(
        solver.Constraint(-solver.infinity(), 0.0)
    )
    c = len(constraints) - 1

    store_partial_name = store[:31] + '|'
    store_shipping_name = store[:31] + '|frete'
    for i in range(len(variables)):
        if store_shipping_name in variables[i].name():
            constraints[c].SetCoefficient(variables[i], -999)
        elif store_partial_name in variables[i].name():
            constraints[c].SetCoefficient(variables[i], 1)
        else:
            constraints[c].SetCoefficient(variables[i], 0)
print('Resolvendo...')
result_status = solver.Solve()
clear_screen()
if result_status == pywraplp.Solver.OPTIMAL:
    print('Temos uma solucao!')
else:
    print('Nao temos a melhor das solucoes')

print('Numero de variaveis: ', solver.NumVariables())
print('Numero de limitadores: ', solver.NumConstraints())
print('Menor valor encontrado (com frete): R$ {}\n\n'
      .format(solver.Objective().Value()))

used_variables = []
for v in variables:
    if v.solution_value() > 0:
        used_variables.append(v)
        # print('{} : {}'.format(v.name(), v.solution_value()))

storenames = set([v.name().split('|')[0] for v in used_variables])
for s in storenames:
    print('Na loja {}:'.format(s))
    for v in used_variables:
        if s in v.name() and '|frete' not in v.name():
            cardname = v.name().split('|')[1]
            for st in stores:
                if s not in st['name']:
                    continue
                for o in st['offers']:
                    if cardname in o['card']:
                        price = o['price']
            print('\t{}* {} ({})'.format(v.solution_value(), cardname, price))
sysexit()
