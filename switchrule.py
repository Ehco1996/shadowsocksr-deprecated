from configloader import load_config, get_config


def getKeys(key_list):
    if get_config().API_INTERFACE == 'ehcomod':
        key_list += ['method', 'obfs', 'protocol','level',]
    return key_list
# return key_list + ['plan'] # append the column name 'plan'


def isTurnOn(row):
    return True
    # return row['plan'] == 'B' # then judge here
