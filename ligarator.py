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
SHIPPING = float(input(
    'Qual o valor a ser considerado de frete?(Formato: xx.yy):\n'))
clear_screen()

print('Na janela a seguir selecione o nome do arquivo que contem a sua want.')
print('As cartas precisam estar uma por linha.')
print('No seguinte formato: [N] [cardname]')
print('Ex: 4 Guard Gomazoa')
input('Pressione enter para continuar')
clear_screen()

root = tk.Tk()
root.withdraw()
FILEPATH = filedialog.askopenfilename()
filepaths = make_filepaths(FILEPATH)


try:
    with open('banned_stores.txt', 'r', encoding='utf-8') as f:
        banned_stores = [e.strip() for e in f.readlines() if len(e) > 0]
except Exception as e:
    banned_stores = []

# checks if we have offers already loaded
offers = False
loaded_offers = load_offers_from_file(filepaths['offers'])
if loaded_offers is not False:
    print('Encontramos uma lista de ofertas para esta wantlist.')
    r = input('Deseja utilizar as ofertas já carregadas? (S/N)')
    if r.upper() in ['S', 'Y', 'SIM']:
        offers = loaded_offers
        loaded_offers = None

# GET WANTLIST
clear_screen()
if offers is False:
    with open(filepaths['entry'], 'r', encoding='utf-8') as f:
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
        else:
            new_offers = [
                o for o in new_offers
                if o['store'] not in banned_stores
            ]
        print('\ttemos {} ofertas!'.format(len(new_offers)))
        offers += new_offers
        sleeptime = randint(5, 10)
        print('\tdormindo por {} segundos'.format(sleeptime))
        time.sleep(sleeptime)

# cleans the offers and saves them to file to allow for re-processing later
offers = clean_store_offers(offers, banned_stores)
save_offers_to_file(offers, filepaths['offers'])

# separate card offers per store
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
solver = Solver(
    'SolveIntegerProblem', pywraplp.Solver.CBC_MIXED_INTEGER_PROGRAMMING)


# Prepare variables
variables = []
for s in stores:
    for o in s['offers']:
        numvar = solver.IntVar(0.0, o['stock'], (s['name'], o['card']))
        variables.append(numvar)

# Shipping as variables
for s in stores:
    # varname = s['name'][:31] + '|frete'
    numvar = solver.IntVar(0.0, 1.0, (s['name'], 'frete'))
    variables.append(numvar)

# build the objective, part 1: set coeficients
objective = solver.Objective()
i = -1
for s in stores:
    for o in s['offers']:
        i += 1
        objective.SetCoefficient(variables[i], o['price'])

for s in stores:
    i += 1
    objective.SetCoefficient(variables[i], s['shipping'])
# objective: minimize the total value
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

    # constraint: must buy X of that card
    constraints.append(
        solver.Constraint(wanted_quantity, wanted_quantity)
    )
    c = len(constraints) - 1

    for i in range(len(variables)):
        if card == variables[i].card_name:
            constraints[c].SetCoefficient(variables[i], 1)
        else:
            constraints[c].SetCoefficient(variables[i], 0)

# constraint: must buy shipping for each store
# in this restriction, we set the coeficient of each card in that store to 1
# and the coeficient of the shipping to -999
# and the constraint as "less than zero"
# that way, when one card is bought, the shipping must also be bought to offset
# the value in this equation
for store in storenames:
    constraints.append(
        solver.Constraint(-solver.infinity(), 0.0)
    )
    c = len(constraints) - 1

    for i in range(len(variables)):
        if variables[i].store_name == store:
            if variables[i].card_name == 'frete':
                constraints[c].SetCoefficient(variables[i], -999)
            else:
                constraints[c].SetCoefficient(variables[i], 1)
        else:
            constraints[c].SetCoefficient(variables[i], 0)

print('Resolvendo...')
result_status = solver.Solve()
clear_screen()
if result_status == pywraplp.Solver.OPTIMAL:
    print('Temos uma solucao!')
else:
    print('Nao foi possivel encontrar uma solucao')
    sys.exit()

with open(filepaths['buylist'], 'w+', encoding='utf-8') as f:
    print('Numero de variaveis: ', solver.NumVariables())
    print('Numero de limitadores: ', solver.NumConstraints())
    print('Menor valor encontrado (com frete): R$ {}\n\n'
          .format(solver.Objective().Value()))
    f.write('Numero de variaveis: {}\n'.format(solver.NumVariables()))
    f.write('Numero de limitadores: {}\n'.format(solver.NumConstraints()))
    f.write('Menor valor encontrado (com frete): R$ {}\n\n'
            .format(solver.Objective().Value()))

    used_variables = [v for v in variables if v.solution_value() > 0]

    storenames = set([v.store_name for v in used_variables])
    for s in storenames:
        print('Na loja {}:'.format(s))
        f.write('Na loja {}:\n'.format(s))
        for v in used_variables:
            if v.store_name == s and v.card_name != 'frete':
                for st in stores:
                    if st['name'] != s:
                        continue
                    for o in st['offers']:
                        if o['card'] == v.card_name:
                            price = o['price']
                print('\t{:d}* {} (R${:.2f} cada)'
                      .format(int(v.solution_value()), v.card_name, price))
                f.write('\t{:d}* {} (R${:.2f} cada)\n'
                        .format(int(v.solution_value()), v.card_name, price))
sysexit()
