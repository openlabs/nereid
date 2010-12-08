from nereid.application import Nereid

app = Nereid(TRYTON_CONFIG='../Tryton/1.8/etc/trytond.conf', DATABASE_NAME='email')

@app.route('/')
def home():
    parties = app.pool.get('party.party').search([])
    return "Party IDs are: %s" % parties


app.run(use_debugger=True)

