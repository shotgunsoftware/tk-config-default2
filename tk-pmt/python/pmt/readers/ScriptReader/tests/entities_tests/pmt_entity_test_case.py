import unittest

from readers.ScriptReader.entities import *
from readers.ScriptReader.entities_discrepancies import PMTEntitiesDiscrepancies


class PMTEntityTestCase(unittest.TestCase):
    """Class to use in place of unittest.TestCase when comparing equality of two PMT Projects.
    In case of assertion error, a detailed report explaining the discrepancies between the
    two Projects is displayed.
    """

    def __init__(self, *args):
        super().__init__(*args)

        self.addTypeEqualityFunc(PMTEntity, "assertPMTEntityEqual")
        self.addTypeEqualityFunc(Asset, "assertPMTEntityEqual")
        self.addTypeEqualityFunc(Sequence, "assertPMTEntityEqual")
        self.addTypeEqualityFunc(Project, "assertPMTEntityEqual")

    def assertPMTEntityEqual(self, pmt_entity1, pmt_entity2, msg=None):

        # Use standard equality comparison
        if not pmt_entity1 == pmt_entity2:
            # If the entities are not equal, report the discrepancies
            discrepancies = PMTEntitiesDiscrepancies.analyze(
                pmt_entity1, pmt_entity2
            )
            msg = discrepancies.report()
            msg = self._formatMessage(
                f"{pmt_entity1} is not equal to {pmt_entity2}", msg
            )
            self.fail(msg)
