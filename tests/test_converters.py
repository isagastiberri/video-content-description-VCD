"""
VCD (Video Content Description) library v4.2.0

Project website: http://vcd.vicomtech.org

Copyright (C) 2020, Vicomtech (http://www.vicomtech.es/),
(Spain) all rights reserved.

VCD is a Python library to create and manage VCD content version 4.2.0.
VCD is distributed under MIT License. See LICENSE.

"""


import unittest
import json
import os
import sys
sys.path.insert(0, "..")
import converters.vcdConverter.converter as converter


class TestBasic(unittest.TestCase):

    ###########################################################
    ### From VCD3.3 to VCD4.1
    ###########################################################
    # Converter from VCD 3.3.0 to VCD 4.2.0 (3DOD cuboids)
    def test_VCD330_to_VCD420_3dod(self):
        vcd330_file_name = "./etc/in/vcd330_sample_3dod.json"
        myConverter = converter.ConverterVCD330toVCD420(vcd330_file_name)
        vcd = myConverter.get()

        if not os.path.isfile('./etc/vcd420_sample_3dod.json'):
            vcd.save('./etc/vcd420_sample_3dod.json', False)

    # Converter from VCD 3.3.0 to VCD 4.2.0 (LS poly3d)
    def test_VCD330_to_VCD420_ls(self):
        vcd330_file_name = "./etc/in/vcd330_sample_ls.json"
        myConverter = converter.ConverterVCD330toVCD420(vcd330_file_name)
        vcd = myConverter.get()

        if not os.path.isfile('./etc/vcd420_sample_ls.json'):
            vcd.save('./etc/vcd420_sample_ls.json', False)

    # Converter from VCD 3.3.0 to VCD 4.2.0 (PD poly2d)
    def test_VCD330_to_VCD420_pd(self):
        vcd330_file_name = "./etc/in/vcd330_sample_pd.json"
        myConverter = converter.ConverterVCD330toVCD420(vcd330_file_name)
        vcd = myConverter.get()

        if not os.path.isfile('./etc/vcd420_sample_pd.json'):
            vcd.save('./etc/vcd420_sample_pd.json', False)

    def test_VCD330_to_VCD420_KITTI_tracking(self):
        vcd330_file_name = "./etc/in/vcd330_kitti_tracking_0_fw.json"
        myConverter = converter.ConverterVCD330toVCD420(vcd330_file_name)
        vcd = myConverter.get()

        if not os.path.isfile('./etc/vcd420_kitti_tracking_0_from_vcd330fw.json'):
            vcd.save('./etc/vcd420_kitti_tracking_0_from_vcd330fw.json', False)

    def test_VCD330_to_VCD420_semantics(self):
        vcd330_file_name = "./etc/in/vcd330_semantics_fw.json"
        myConverter = converter.ConverterVCD330toVCD420(vcd330_file_name)
        vcd = myConverter.get()

        if not os.path.isfile('./etc/vcd420_semantics_fw.json'):
            vcd.save('./etc/vcd420_semantics_fw.json', False)

    def test_VCD330_to_VCD420_mesh(self):
        vcd330_file_name = "./etc/in/vcd330_sample_mesh_short.json"
        myConverter = converter.ConverterVCD330toVCD420(vcd330_file_name)
        vcd = myConverter.get()

        if not os.path.isfile('./etc/vcd420_sample_mesh_short.json'):
            vcd.save('./etc/vcd420_sample_mesh_short.json', False)


    ###########################################################
    ### From VCD4 to VCD3.3
    ###########################################################
    # Converter from VCD 3.3.0 to VCD 4.2.0 (DMD)
    def test_VCD420_to_VCD330_dmd(self):
        vcd420_file_name = "./etc/in/vcd420_1_attm03-08.json"
        myConverter = converter.ConverterVCD420toVCD330(vcd420_file_name)
        vcd = myConverter.get()

        if not os.path.isfile('./etc/vcd330_1_attm03-08.json'):
            file = open('./etc/vcd330_1_attm03-08.json', 'w')
            file.write(json.dumps(vcd))
            file.close()

    # Converter from VCD 3.3.0 to VCD 4.2.0
    def test_VCD420_to_VCD330_3dod(self):
        vcd420_file_name = "./etc/vcd420_sample_3dod.json"
        myConverter = converter.ConverterVCD420toVCD330(vcd420_file_name)
        vcd = myConverter.get()

        if not os.path.isfile('./etc/vcd330_from_vcd420_sample_3dod.json'):
            file = open('./etc/vcd330_from_vcd420_sample_3dod.json', 'w')
            file.write(json.dumps(vcd))
            file.close()

    # Converter from VCD 3.3.0 to VCD 4.2.0
    def test_VCD420_to_VCD330_ls(self):
        vcd420_file_name = "./etc/vcd420_sample_ls.json"
        myConverter = converter.ConverterVCD420toVCD330(vcd420_file_name)
        vcd = myConverter.get()

        if not os.path.isfile('./etc/vcd330_from_vcd420_sample_ls.json'):
            file = open('./etc/vcd330_from_vcd420_sample_ls.json', 'w')
            file.write(json.dumps(vcd))
            file.close()

    # Converter from VCD 3.3.0 to VCD 4.2.0 (PD poly2d)
    def test_VCD420_to_VCD330_pd(self):
        vcd420_file_name = "./etc/vcd420_sample_pd.json"
        myConverter = converter.ConverterVCD420toVCD330(vcd420_file_name)
        vcd = myConverter.get()

        if not os.path.isfile('./etc/vcd330_from_vcd420_sample_pd.json'):
            file = open('./etc/vcd330_from_vcd420_sample_pd.json', 'w')
            file.write(json.dumps(vcd, indent=4, sort_keys=True))
            file.close()

    # Converter from VCD 3.3.0 to VCD 4.2.0
    def test_VCD420_to_VCD330_semantics(self):
        vcd420_file_name = "./etc/vcd420_semantics_fw.json"
        myConverter = converter.ConverterVCD420toVCD330(vcd420_file_name)
        vcd = myConverter.get()

        if not os.path.isfile('./etc/vcd330_from_vcd420_semantics_fw.json'):
            file = open('./etc/vcd330_from_vcd420_semantics_fw.json', 'w')
            file.write(json.dumps(vcd, indent=4, sort_keys=True))
            file.close()

    def test_VCD420_to_VCD330_mesh(self):
        vcd420_file_name = "./etc/vcd420_sample_mesh_short.json"
        myConverter = converter.ConverterVCD420toVCD330(vcd420_file_name)
        vcd = myConverter.get()

        if not os.path.isfile('./etc/vcd330_from_vcd420_sample_mesh_short.json'):
            file = open('./etc/vcd330_from_vcd420_sample_mesh_short.json', 'w')
            file.write(json.dumps(vcd, indent=4, sort_keys=True))
            file.close()


if __name__ == '__main__':  # This changes the command-line entry point to call unittest.main()
    print("Running " + os.path.basename(__file__))
    unittest.main()

