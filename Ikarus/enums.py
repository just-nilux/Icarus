TYPE_LIMIT = 'limit'
TYPE_OCO = 'oco'
TYPE_MARKET = 'market'

PHASE_ENTER = 'enter'
PHASE_EXIT = 'exit'

STAT_OPEN_ENTER = 'open_enter'
STAT_ENTER_EXP = 'enter_expire'
STAT_WAITING_EXIT = 'waiting_exit'
STAT_OPEN_EXIT = 'open_exit'
STAT_EXIT_EXP = 'exit_expire'
STAT_CLOSED = 'closed'
STAT_PART_CLOSED_ENTER = 'partially_closed_enter'
STAT_PART_CLOSED_EXIT = 'partially_closed_exit'

ACTN_CANCEL = 'cancel'
ACTN_UPDATE = 'update'
ACTN_POSTPONE = 'postpone'
ACTN_MARKET_ENTER = 'market_enter'
ACTN_MARKET_EXIT = 'market_exit'
ACTN_EXEC_EXIT = 'execute_exit'

CAUSE_MANUAL_CHANGE = 'manual_change'

EVENT_CANCELED = 'canceled'
EVENT_FILLED = 'filled'

# TODO: Move this function to utils
def get_lto_phase(lto):

    if lto['status'] in [STAT_OPEN_ENTER, STAT_ENTER_EXP]:
        return PHASE_ENTER

    elif lto['status'] in [STAT_EXIT_EXP, STAT_OPEN_EXIT, STAT_WAITING_EXIT]:
        return PHASE_EXIT

    else:
        raise Exception(f'LTO {lto["_id"]} status {lto["status"]}')