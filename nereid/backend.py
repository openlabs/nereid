#This file is part of Tryton & Nereid. The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.


class TransactionManager(object):

    def __init__(self, database_name, user, context=None):
        self.database_name = database_name
        self.user = user
        self.context = context if context is not None else {}

    def __enter__(self):
        from trytond.transaction import Transaction
        Transaction().start(
            self.database_name, self.user,
            readonly=False, context=self.context.copy()
        )
        return Transaction()

    def __exit__(self, type, value, traceback):
        from trytond.transaction import Transaction
        Transaction().stop()
