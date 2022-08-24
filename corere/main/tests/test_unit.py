# import unittest
from django.test import SimpleTestCase
from corere.main.views import classes as cl

class HelperTestCase(SimpleTestCase):
    # def setUp(self):
    #     pass

    #file_check returns "" if no issue with path+name, otherwise returns a string with the issue
    def test_helper_sanitary_file_check(self):
        self.assertFalse(cl._helper_sanitary_file_check("/good"))
        self.assertFalse(cl._helper_sanitary_file_check("/good/good"))
        self.assertFalse(cl._helper_sanitary_file_check("/good/good/good"))

        self.assertFalse(cl._helper_sanitary_file_check("/good."))
        self.assertFalse(cl._helper_sanitary_file_check("/good/good."))
        self.assertFalse(cl._helper_sanitary_file_check("/good/good/good."))

        self.assertFalse(cl._helper_sanitary_file_check("/g /good"))
        self.assertFalse(cl._helper_sanitary_file_check("/G/good"))
        self.assertFalse(cl._helper_sanitary_file_check("/1/good"))
        self.assertFalse(cl._helper_sanitary_file_check("/_/good"))
        self.assertFalse(cl._helper_sanitary_file_check("/-/good"))
        self.assertFalse(cl._helper_sanitary_file_check("/./good"))

        self.assertTrue(cl._helper_sanitary_file_check(""))
        self.assertTrue(cl._helper_sanitary_file_check("bad"))
        self.assertTrue(cl._helper_sanitary_file_check("bad/"))
        self.assertTrue(cl._helper_sanitary_file_check("/bad/"))
        self.assertTrue(cl._helper_sanitary_file_check("/bad/bad/"))
        self.assertTrue(cl._helper_sanitary_file_check("/bad/bad/bad/"))
        self.assertTrue(cl._helper_sanitary_file_check("//bad/bad"))
        self.assertTrue(cl._helper_sanitary_file_check("/  /bad/bad"))
        
        self.assertTrue(cl._helper_sanitary_file_check("/bad/.."))
        self.assertTrue(cl._helper_sanitary_file_check("/bad/..bad"))
        self.assertTrue(cl._helper_sanitary_file_check("/bad/....bad"))
        self.assertTrue(cl._helper_sanitary_file_check("/bad../"))
        self.assertTrue(cl._helper_sanitary_file_check("/..bad/"))
        self.assertTrue(cl._helper_sanitary_file_check("/..bad../"))
        self.assertTrue(cl._helper_sanitary_file_check("../bad/"))

        self.assertTrue(cl._helper_sanitary_file_check("/*"))
        self.assertTrue(cl._helper_sanitary_file_check("/?"))
        self.assertTrue(cl._helper_sanitary_file_check("/\""))
        self.assertTrue(cl._helper_sanitary_file_check("/<"))
        self.assertTrue(cl._helper_sanitary_file_check("/>"))
        self.assertTrue(cl._helper_sanitary_file_check("/|"))
        self.assertTrue(cl._helper_sanitary_file_check("/;"))
        self.assertTrue(cl._helper_sanitary_file_check("/#"))
        self.assertTrue(cl._helper_sanitary_file_check("/:"))
        self.assertTrue(cl._helper_sanitary_file_check("//"))
        self.assertTrue(cl._helper_sanitary_file_check("/\\"))
        self.assertTrue(cl._helper_sanitary_file_check("/ * ? \" < > | ; # : \ "))

        self.assertTrue(cl._helper_sanitary_file_check("/bad!/bad"))
        self.assertTrue(cl._helper_sanitary_file_check("/!/bad"))