"""
VCD (Video Content Description) library v4.0.0

Project website: http://vcd.vicomtech.org

Copyright (C) 2020, Vicomtech (http://www.vicomtech.es/),
(Spain) all rights reserved.

VCD is a Python library to create and manage VCD content version 4.0.0.
VCD is distributed under MIT License. See LICENSE.

"""


import copy
import json
import warnings
from jsonschema import validate
from enum import Enum

import vcd.utils as utils
import vcd.schema as schema


class ElementType(Enum):
    """
    Elements of VCD (Object, Action, Event, Context, Relation)
    """
    object = 1
    action = 2
    event = 3
    context = 4
    relation = 5


class SensorType(Enum):
    """
    Type of sensor.
    """
    video = 1
    pointCloud = 2
    other = 3


class RDF(Enum):
    """
    Type of RDF agent (subject or object)
    """
    subject = 1
    object = 2


class VCD:
    """
    VCD class as main container of VCD content. Exposes functions to
    add Elements, to get information and to remove data.
    Internally manages all information as Python dictionaries, and can map
    data into JSON strings.
    """
    ##################################################
    # Constructor
    ##################################################
    def __init__(self, file_name=None, validation=False):

        if file_name is not None:
            # NOTE: json.load reads the file and creates the entries of the dictionary. However, JSON uses always
            # strings for the keys. Though, in VCD I am using integers as keys in many sub-dictionaries (e.g. frames,
            # objects, etc.).
            # In practice, there is no major problem, since VCD usage is always through JSON, and json.dumps always
            # convert all internal integers into strings.
            # However, the problem comes when stringifying VCD native content (not loaded), because the ordering of
            # keys is different if they are integers or strings. In the case of integers, ordering keeps the natural
            # order of numbers: 1, 2, 4, ..., 10, 11. While ordering of strings ignores the amount of digits: "10", "11"
            # , "1", "2", "4"...
            # This different sorting approaches makes comparisons difficult, and if a VCD is loaded and then saved,
            # it will be less human-readable.
            # The following lambda function reads the key strings and those that are integers are actually stored
            # as integers.
            # self.data = json.load(json_file)  # Reads keys as strings.
            # Following lines converts string keys which are numbers into actual integers.

            # Validate if the provided VCD file follows the schema
            # Open converting strings into integers for the dict, as explained above

            if validation:
                json_file = open(file_name)
                temp_data = json.load(json_file)  # Open without converting strings to integers

                self.schema = schema.vcd_schema
                if 'version' in temp_data['vcd']:
                    if temp_data['vcd']['version'] == "4.0.0":
                        validate(instance=temp_data, schema=self.schema)  # Raises errors if not validated
                    elif temp_data['vcd']['version'] == "3.3.0":
                        warnings.warn("ERROR: This file is not a VCD 4.0.0 file.")
                    else:
                        warnings.warn("ERROR: Can't read input file: unsupported VCD format")
                else:
                    warnings.warn("ERROR: Can't read input file: this is not a valid VCD JSON file")

                json_file.close()

            # Proceed normally to open file and load the dictionary, converting strings into integers
            json_file = open(file_name)
            self.data = json.load(
                json_file,
                object_hook=lambda d: {int(k) if k.lstrip('-').isdigit() else k: v for k, v in d.items()}
            )
            json_file.close()

            # Final set-up
            self.__compute_last_uid()
            self.__compute_object_data_names()

        else:
            # Main VCD data
            self.data = {'vcd': {}}
            self.data['vcd']['frames'] = {}
            self.data['vcd']['version'] = "4.0.0"
            self.data['vcd']['frame_intervals'] = []

            # Schema information
            self.schema = schema.vcd_schema

            # Additional auxiliary structures
            self.__lastUID = dict()
            self.__lastUID[ElementType.object] = -1
            self.__lastUID[ElementType.action] = -1
            self.__lastUID[ElementType.event] = -1
            self.__lastUID[ElementType.context] = -1
            self.__lastUID[ElementType.relation] = -1

            self.__object_data_names = {}  # Stores names of ObjectData, e.g. "age", or "width" per Object

    ##################################################
    # Private API: inner functions
    ##################################################
    def __get_uid_to_assign(self, element_type, uid):
        assert isinstance(element_type, ElementType)  # not sure if this evaluates correctly
        if uid is None:
            self.__lastUID[element_type] += 1  # If None is provided, let's use the next one available
            uid_to_assign = self.__lastUID[element_type]
            return uid_to_assign

        # uid is not None
        # There are already this type of elements in vcd
        if uid > self.__lastUID[element_type]:
            self.__lastUID[element_type] = uid
            uid_to_assign = self.__lastUID[element_type]
        else:
            uid_to_assign = uid
        return uid_to_assign

    def __update_frame_intervals_of_vcd(self, frame_intervals):
        if len(frame_intervals) == 0:
            return

        assert(isinstance(frame_intervals, list))

        # Fuse with existing
        fit = copy.deepcopy(frame_intervals)
        fis = self.data['vcd'].setdefault('frame_intervals', [])
        fit += fis

        # Now substitute
        fit_fused = utils.fuse_frame_intervals(fit)
        self.data['vcd']['frame_intervals'] = fit_fused

    def __remove_element_frame_interval(self, element_type, uid, frame_interval_dict):
        # This function removes a frameInterval from an element
        if uid in self.data['vcd'][element_type.name + 's']:
            fis = self.data['vcd'][element_type.name + 's'][uid]['frame_intervals']

            fi_dict_array_to_add = []
            for idx, fi in enumerate(fis):
                # Three options: 1) no intersection 2) one inside 3) intersection
                max_start_val = max(frame_interval_dict['frame_start'], fi['frame_start'])
                min_end_val = min(frame_interval_dict['frame_end'], fi['frame_end'])

                if frame_interval_dict['frame_start'] <= fi['frame_start'] \
                        and frame_interval_dict['frame_end'] >= fi['frame_end']:
                    # Case c) equal tuples -> delete or Case f) interval to delete covers completely target interval
                    del fis[idx]

                if max_start_val <= min_end_val:
                    # There is some intersection: cases a, b, d and e

                    if max_start_val == fi['frame_start']:  # cases a, b
                        new_fi = {'frame_start': min_end_val + 1, 'frame_end': fi['frame_end']}
                        fis[idx] = new_fi

                    elif min_end_val == fi['frame_end']:  # case e
                        new_fi = {'frame_start': fi['frame_start'], 'frame_end': max_start_val - 1}
                        fis[idx] = new_fi
                    else:  # case d maxStartVal > fi_tuple[0] and minEndVal < fi_tuple[1]
                        # Inside: then we need to split into two frame intervals
                        new_fi_1 = {'frame_start': fi['frame_start'], 'frame_end': max_start_val - 1}
                        new_fi_2 = {'frame_start': min_end_val + 1, 'frame_end': fi['frame_end']}
                        fis[idx] = new_fi_1
                        fi_dict_array_to_add.append(new_fi_2)

            for fi_dict_to_add in fi_dict_array_to_add:
                fis.append(fi_dict_to_add)

    def __compute_frame_intervals(self):
        for frame_num in self.data['vcd']['frames']:
            found = False
            for fi in self.data['vcd']['frame_intervals']:
                if utils.is_inside(frame_num, fi):
                    found = True
            if not found:
                # This frame is not included in the frameIntervals, let's modify them
                idx_to_fuse = []
                for index, fi in enumerate(self.data['vcd']['frame_intervals']):
                    if utils.intersects(fi, utils.as_frame_interval_dict(frame_num)) \
                            or utils.consecutive(fi, utils.as_frame_interval_dict(frame_num)):
                        idx_to_fuse.append(index)
                if len(idx_to_fuse) == 0:
                    # New frameInterval, separated
                    self.data['vcd']['frame_intervals'].append({'frame_start': frame_num, 'frame_end': frame_num})
                else:
                    new_list = []
                    fused_fi = utils.as_frame_interval_dict(frame_num)
                    for index, fi_ in enumerate(self.data['vcd']['frame_intervals']):
                        if index in idx_to_fuse:
                            fused_fi = (min(fused_fi['frame_start'], fi_['frame_start']),
                                        max(fused_fi['frame_end'], fi_['frame_end']))
                        else:
                            new_list.append(fi_)  # also add those not affected by fusion

                    new_list.append(fused_fi)
                    self.data['vcd']['frame_intervals'] = new_list

    def __add_frame(self, frame_num):
        # self.data['vcd']['frames'].setdefault(frame_num, {}) # 3.8 secs - 10.000 times
        if frame_num not in self.data['vcd']['frames']:
            self.data['vcd']['frames'][frame_num] = {}

    def __compute_last_uid(self):
        self.__lastUID = dict()
        # Read all objects and fill lastUID
        self.__lastUID[ElementType.object] = -1
        if 'objects' in self.data['vcd']:
            for uid in self.data['vcd']['objects']:
                if int(uid) > self.__lastUID[ElementType.object]:
                    self.__lastUID[ElementType.object] = int(uid)

        self.__lastUID[ElementType.action] = -1
        if 'actions' in self.data['vcd']:
            for uid in self.data['vcd']['actions']:
                if int(uid) > self.__lastUID[ElementType.action]:
                    self.__lastUID[ElementType.action] = int(uid)

        self.__lastUID[ElementType.event] = -1
        if 'events' in self.data['vcd']:
            for uid in self.data['vcd']['events']:
                if int(uid) > self.__lastUID[ElementType.event]:
                    self.__lastUID[ElementType.event] = int(uid)

        self.__lastUID[ElementType.context] = -1
        if 'contexts' in self.data['vcd']:
            for uid in self.data['vcd']['contexts']:
                if int(uid) > self.__lastUID[ElementType.context]:
                    self.__lastUID[ElementType.context] = int(uid)

        self.__lastUID[ElementType.relation] = -1
        if 'relations' in self.data['vcd']:
            for uid in self.data['vcd']['relations']:
                if int(uid) > self.__lastUID[ElementType.relation]:  # uid is a string!
                    self.__lastUID[ElementType.relation] = int(uid)

    def __compute_object_data_names(self):
        self.__object_data_names = {}
        if 'objects' in self.data['vcd']:
            for uid in self.data['vcd']['objects']:
                self.__object_data_names[uid] = set()
                self.__compute_object_data_names_uid(uid)

    def __compute_object_data_names_uid(self, uid):
        # This function recomputes the self.__object_data_names entry for uid
        if uid not in self.__object_data_names:
            return
        del self.__object_data_names[uid]  # Clear list
        if uid in self.data['vcd']['objects']:
            object_ = self.data['vcd']['objects'][uid]
            self.__object_data_names.setdefault(uid, set())
            if 'frame_intervals' in object_:
                # There is dynamic content
                fis = object_['frame_intervals']
                for fi in fis:
                    for frame_num in range(fi['frame_start'], fi['frame_end'] + 1):
                        for objectInFrame in self.data['vcd']['frames'][frame_num]['objects'].values():
                            for valList in objectInFrame['object_data'].values():
                                for val in valList:
                                    if 'name' in val:
                                        self.__object_data_names[uid].add(val['name'])
            if 'object_data' in object_:
                # There is also static content
                for valArray in object_['object_data'].values():
                    for val in valArray:
                        if 'name' in val:
                            self.__object_data_names[uid].add(val['name'])

    def __clean(self):
        # This function recomputes LUTs and other structures used by VCD
        self.__clean_up_frames()
        self.__clean_up_vcd()
        self.__compute_frame_intervals()

    def __clean_up_frames(self):
        # This function explores self.data['vcd']['frames'] and removes entries which are empty
        frames = self.data['vcd']['frames']

        frame_nums_to_remove = []
        for frame_num, frameContent in frames.items():  # so there is an 'objects' key, but its an empty list

            if 'objects' in frameContent and frameContent['objects']:
                continue

            if 'actions' in frameContent and frameContent['actions']:
                continue

            if 'events' in frameContent and frameContent['events']:
                continue

            if 'contexts' in frameContent and frameContent['contexts']:
                continue

            if 'relations' in frameContent and frameContent['relations']:
                continue

            if 'frameProperties' in frameContent:
                continue

            frame_nums_to_remove.append(frame_num)

        # Update LUTs only modifying values changed
        if frame_nums_to_remove:
            for j in sorted(frame_nums_to_remove, reverse=True):  # starting from higher
                del frames[j]

    def __clean_up_vcd(self):
        if 'objects' in self.data['vcd']:
            if not self.data['vcd']['objects']:  # So there is 'objects', but empty
                del self.data['vcd']['objects']

        if 'actions' in self.data['vcd']:
            if not self.data['vcd']['actions']:  # So there is 'actions', but empty
                del self.data['vcd']['actions']

        if 'events' in self.data['vcd']:
            if not self.data['vcd']['events']:  # So there is 'events', but empty
                del self.data['vcd']['events']

        if 'contexts' in self.data['vcd']:
            if not self.data['vcd']['contexts']:  # So there is 'contexts', but empty
                del self.data['vcd']['contexts']

        if 'relations' in self.data['vcd']:
            if not self.data['vcd']['relations']:  # So there is 'relations', but empty
                del self.data['vcd']['relations']

    def __add_frames(self, frame_value, element_type, uid_to_assign):
        # This functions add frame structures to root vcd
        if isinstance(frame_value, int):
            self.__add_frame(frame_value)
            self.data['vcd']['frames'][frame_value].setdefault(element_type.name + 's', {})
            self.data['vcd']['frames'][frame_value][element_type.name + 's'].setdefault(uid_to_assign, {})
        elif isinstance(frame_value, tuple):
            for frame_num in range(frame_value[0], frame_value[1] + 1):
                self.__add_frame(frame_num)
                self.data['vcd']['frames'][frame_num].setdefault(element_type.name + 's', {})
                self.data['vcd']['frames'][frame_num][element_type.name + 's'].setdefault(uid_to_assign, {})
        elif isinstance(frame_value, list):
            for frame_interval in frame_value:
                for frame_num in range(frame_interval[0], frame_interval[1]+1):
                    # 1/3 Create the frame if it doesn't already exist
                    self.__add_frame(frame_num)
                    # 2/3 Fill with entries for this element
                    self.data['vcd']['frames'][frame_num].setdefault(element_type.name + 's', {})
                    # 3/3 Create an empty entry (we only need the pointer at 'frames')
                    # If the entry already exists, it is overwritten to {}
                    self.data['vcd']['frames'][frame_num][element_type.name + 's'].setdefault(uid_to_assign, {})
        else:
            warnings.warn("WARNING: calling __add_frames with " + type(frame_value))

    def __update_frame_intervals(self, fis_dict_existing, frame_value):
        # This function receives a frame_value (int, tuple or list) and fuses with existing fis
        # This function also updates frame intervals of root VCD
        assert(frame_value is not None)  # So this control should be external to this function

        if fis_dict_existing is None:
            fis_dict_existing = []

        if len(fis_dict_existing) == 0:
            # This can happen when a new object/action/... is created
            fis_dict_new = utils.as_frame_intervals_array_dict(frame_value)
            self.__update_frame_intervals_of_vcd(fis_dict_new)
            return fis_dict_new

        # Up to this point, fis_existing has something
        last_frame_end = fis_dict_existing[-1]['frame_end']

        # Next code is about speeding up the updating process
        fis_dict_fused = fis_dict_existing
        is_single_frame = isinstance(frame_value, int)
        if is_single_frame and last_frame_end is not None:
            if last_frame_end == frame_value:
                # Same frame_value, so no need to update anything
                call_full_fusion = False
                pass
            else:
                if frame_value == last_frame_end + 1:
                    # So this is the next frame, let's skip all fusing computation and simply sum 1 to last value
                    if fis_dict_fused[-1]['frame_end'] == last_frame_end:

                        # Confirmed this element was updated last time
                        fis_dict_fused[-1] = {
                            'frame_start': fis_dict_fused[-1]['frame_start'],
                            'frame_end': fis_dict_fused[-1]['frame_end'] + 1
                        }

                        # Now global frame_intervals at VCD (it is guaranteed that last entry was lastFrame)
                        last_vcd_fi_dict = self.data['vcd']['frame_intervals'][-1]

                        # VCD frame intervals need to be updated as well
                        if last_vcd_fi_dict["frame_end"] == last_frame_end:
                            # This is the first object updating this frame
                            self.data['vcd']['frame_intervals'][-1] = {
                                'frame_start': last_vcd_fi_dict["frame_start"],
                                'frame_end': last_vcd_fi_dict["frame_end"] + 1
                            }
                        elif last_vcd_fi_dict["frame_end"] == frame_value:
                            # No need to update
                            pass
                        else:
                            # Ok, need to update VCD frame intervals analyzing it entirely
                            self.__update_frame_intervals_of_vcd(fis_dict_fused)

                        call_full_fusion = False
                    else:
                        # This element wasn't updated last time
                        call_full_fusion = True
                else:
                    # Let's compute fusion normally
                    call_full_fusion = True
        else:
            # So we are given a tuple or list, let's go through the entire fusion process
            call_full_fusion = True

        if call_full_fusion:
            if frame_value is not None:
                if is_single_frame:
                    fi_dict_new = {'frame_start': frame_value, 'frame_end': frame_value}
                    fis_dict_fused = utils.fuse_frame_interval_dict(fi_dict_new, fis_dict_existing)
                else:
                    fis_dict_new = utils.as_frame_intervals_array_dict(frame_value)
                    fis_dict_existing.extend(fis_dict_new)

                    fis_dict_fused = utils.fuse_frame_intervals(fis_dict_existing)
            else:
                fis_dict_fused = fis_dict_existing  # Use those existing

            # Update also intervals of VCD
            self.__update_frame_intervals_of_vcd(fis_dict_fused)

        return fis_dict_fused

    def __add_element(
            self, element_type, name, semantic_type='', frame_value=None, uid=None, ont_uid=None,
            stream=None
    ):
        if frame_value is not None:
            assert(isinstance(frame_value, (int, tuple, list)))

        # 1/5 Get uid to assign
        # This function checks if the uid exists (keeps it), or if not, and if it is None
        uid_to_assign = self.__get_uid_to_assign(element_type, uid)
        # Get existing frame intervals
        fis_dicts_existing = []
        if element_type.name + 's' in self.data['vcd']:
            if uid_to_assign in self.data['vcd'][element_type.name + 's']:
                # This element already exists: we need to fuse frame_value with the existing frame_intervals
                element = self.data['vcd'][element_type.name + 's'][uid_to_assign]
                fis_dicts_existing = element.setdefault('frame_intervals', [])

        if frame_value is not None:
            # 2/5 Update elements frame_intervals
            fis_dicts_updated = self.__update_frame_intervals(fis_dicts_existing, frame_value)

            # 3/5 Create 'frames' for newly added frames with pointers
            self.__add_frames(frame_value, element_type, uid_to_assign)
        else:
            # Nothing about frame intervals to be updated
            fis_dicts_updated = fis_dicts_existing

        # 4/5 Create/update Element
        self.__create_update_element(
            element_type, name, semantic_type, fis_dicts_updated, uid_to_assign, ont_uid, stream
        )

        return uid_to_assign

    def __update_element(self, element_type, uid, frame_value):
        assert(isinstance(element_type, ElementType))
        assert(isinstance(uid, int))

        # Check if this uid exists
        if uid not in self.data['vcd'][element_type.name + 's']:
            warnings.warn("WARNING: trying to update a non-existing Element.")
            return

        # Read existing data about this element, so we can call __add_element
        name = self.data['vcd'][element_type.name + 's'][uid]['name']
        semantic_type = self.data['vcd'][element_type.name + 's'][uid]['type']
        ont_uid = None
        stream = None
        if 'ontology_uid' in self.data['vcd'][element_type.name + 's'][uid]:
            ont_uid = self.data['vcd'][element_type.name + 's'][uid]['ontology_uid']
        if 'stream' in self.data['vcd'][element_type.name + 's'][uid]:
            stream = self.data['vcd'][element_type.name + 's'][uid]['stream']

        # Call __add_element (which internally creates OR updates)
        self.__add_element(element_type, name, semantic_type, frame_value, uid, ont_uid, stream)

    def __create_update_element(
            self, element_type, name, semantic_type, frame_intervals_dicts, uid, ont_uid=None, stream=None
    ):
        # This function creates OR updates an element at the root of VCD using the given information
        element_data = {'name': name, 'type': semantic_type, 'frame_intervals': frame_intervals_dicts}

        # Check existing data and append to element_data
        if (ont_uid is not None) and self.get_ontology(ont_uid) is not None:
            element_data['ontology_uid'] = ont_uid

        # Check Stream codename existence
        if stream is not None:
            if 'metadata' in self.data['vcd']:
                if 'streams' in self.data['vcd']['metadata']:
                    if stream in self.data['vcd']['metadata']['streams']:
                        element_data['stream'] = stream
            else:
                warnings.warn('WARNING: trying to add ObjectData for non-declared Stream. Use vcd.addStream.')

        # Check data if object
        if element_type is ElementType.object:
            if 'objects' in self.data['vcd']:
                if uid in self.data['vcd']['objects']:
                    if 'object_data' in self.data['vcd']['objects'][uid]:
                        element_data['object_data'] = self.data['vcd']['objects'][uid]['object_data']
        # Check if relation
        elif element_type is ElementType.relation:
            if 'relations' in self.data['vcd']:
                if uid in self.data['vcd']['relations']:
                    if 'rdf_subjects' in self.data['vcd']['relations'][uid]:
                        element_data['rdf_subjects'] = self.data['vcd']['relations'][uid]['rdf_subjects']
                    if 'rdf_objects' in self.data['vcd']['relations'][uid]:
                        element_data['rdf_objects'] = self.data['vcd']['relations'][uid]['rdf_objects']

        self.data['vcd'].setdefault(element_type.name + 's', {})
        self.data['vcd'][element_type.name + 's'][uid] = element_data  # This call creates or updates the element data

    def __update_object_data(self, uid, object_data, frame_intervals):
        # 1/2 Check Stream codename existence
        stream_valid = False
        if 'in_stream' in object_data.data:
            if 'metadata' in self.data['vcd']:
                if 'streams' in self.data['vcd']['metadata']:
                    for stream_ in self.data['vcd']['metadata']['streams']:
                        if object_data.data['in_stream'] == stream_['name']:
                            stream_valid = True
            if not stream_valid:
                warnings.warn('WARNING: trying to add ObjectData for non-declared Stream. Use vcd.addStream.')

        # 2/2 Fill-in object data...
        # 2.1/2 As "static" content at ['vcd']['objects']...
        if not frame_intervals:
            if uid in self.data['vcd']['objects']:
                object_ = self.data['vcd']['objects'][uid]
                # This is static content that goes into static part of Object
                object_.setdefault('object_data', dict())  # Creates 'object_data' if it does not exist
                object_['object_data'].setdefault(object_data.type.name, []).append(object_data.data)
            else:
                warnings.warn("WARNING: Trying to add ObjectData to non-existing Object, uid: " + str(uid))
        # 2.2/2 OR as "dynamic" content at ['vcd']['frames']...
        else:
            # Create frames (if already existing __add_frames manages the situation
            # Loop and fill
            for fi in frame_intervals:
                for frame_num in range(fi['frame_start'], fi['frame_end'] + 1):
                    self.data['vcd']['frames'][frame_num].setdefault('objects', {})

                    if uid in self.data['vcd']['frames'][frame_num]['objects']:
                        object_ = self.data['vcd']['frames'][frame_num]['objects'][uid]
                        object_.setdefault('object_data', dict())  # Creates 'object_data' if it does not exist
                        object_['object_data'].setdefault(object_data.type.name, []).append(object_data.data)

                    else:  # need to create this entry, only with the pointer (uid) and the data
                        self.data['vcd']['frames'][frame_num]['objects'][uid] = (
                            {'object_data': {
                                object_data.type.name: [object_data.data]
                            }}
                        )

    ##################################################
    # Public API: add, update
    ##################################################
    def add_metadata_properties(self, properties):
        assert(isinstance(properties, dict))
        prop = self.data['vcd']['metadata'].setdefault('properties', dict())
        prop.update(properties)

    def add_name(self, name):
        assert(type(name) is str)
        self.data['vcd']['name'] = name

    def add_annotator(self, annotator):
        assert(type(annotator) is str)
        if 'metadata' not in self.data['vcd']:
            self.data['vcd']['metadata'] = {}
        self.data['vcd']['metadata']['annotator'] = annotator

    def add_comment(self, comment):
        assert(type(comment) is str)
        if 'metadata' not in self.data['vcd']:
            self.data['vcd']['metadata'] = {}
        self.data['vcd']['metadata']['comment'] = comment

    def add_ontology(self, ontology_name):
        self.data['vcd'].setdefault('ontologies', dict())
        for ont_uid in self.data['vcd']['ontologies']:
            if self.data['vcd']['ontologies'][ont_uid] == ontology_name:
                warnings.warn('WARNING: adding an already existing ontology')
                return None
        length = len(self.data['vcd']['ontologies'])
        self.data['vcd']['ontologies'][length] = ontology_name
        return length

    def add_stream(self, stream_name, uri, description, sensor_type):
        assert(isinstance(stream_name, str))
        assert(isinstance(uri, str))
        assert(isinstance(description, str))

        self.data['vcd'].setdefault('metadata', dict())
        self.data['vcd']['metadata'].setdefault('streams', dict())
        self.data['vcd']['metadata']['streams'].setdefault(stream_name, dict())
        if isinstance(sensor_type, SensorType):
            self.data['vcd']['metadata']['streams'][stream_name] = {
                'description': description, 'uri': uri, 'type': sensor_type.name
            }
        elif isinstance(sensor_type, str):
            self.data['vcd']['metadata']['streams'][stream_name] = {
                'description': description, 'uri': uri, 'type': sensor_type
            }

    def add_frame_properties(self, frame_num, properties):
        assert(isinstance(properties, dict))
        self.__add_frame(frame_num)  # this function internally checks if the frame already exists
        self.data['vcd']['frames'][frame_num].setdefault('frame_properties', dict())
        self.data['vcd']['frames'][frame_num]['frame_properties'].setdefault('properties', dict())
        self.data['vcd']['frames'][frame_num]['frame_properties']['properties'].update(properties)

    def add_stream_properties(self, stream_name, properties, frame_num=None):
        # This function can be used to add stream properties. If frame_num is defined, the information is embedded
        # inside 'frame_properties' of the specified frame. Otherwise, the information is embedded into
        # 'stream_properties' inside 'metadata'.

        assert isinstance(properties, dict), "Properties of Stream should be defined as a dictionary"

        # Find if this stream is declared
        if 'metadata' in self.data['vcd']:
            if 'streams' in self.data['vcd']['metadata']:
                if stream_name in self.data['vcd']['metadata']['streams']:
                    if frame_num is None:
                        # This information is static
                        self.data['vcd']['metadata']['streams'][stream_name].setdefault('stream_properties', dict())
                        self.data['vcd']['metadata']['streams'][stream_name]['stream_properties'].update(properties)
                    else:
                        # This is information of the stream for a specific frame
                        self.__add_frame(frame_num)  # to add the frame in case it does not exist
                        frame = self.data['vcd']['frames'][frame_num]
                        frame.setdefault('frame_properties', dict())
                        frame['frame_properties'].setdefault('streams', dict())
                        frame['frame_properties']['streams'].setdefault(stream_name, dict())
                        frame['frame_properties']['streams'][stream_name].setdefault('stream_properties', dict())
                        frame['frame_properties']['streams'][stream_name]['stream_properties'].update(properties)
                else:
                    warnings.warn('WARNING: Trying to add frame sync about non-existing stream')

    def save(self, file_name, pretty=False):
        string = self.stringify(pretty)
        file = open(file_name, 'w')
        file.write(string)
        file.close()

    def validate(self, stringified_vcd):
        temp = json.loads(stringified_vcd)
        if not hasattr(self, 'schema'):
            self.schema = schema.vcd_schema
        validate(instance=temp, schema=self.schema)

    def stringify(self, pretty=True, validation=True):
        if pretty:
            stringified_vcd = json.dumps(self.data, indent=4, sort_keys=True)
        else:
            stringified_vcd = json.dumps(self.data)
        if validation:
            self.validate(stringified_vcd)
        return stringified_vcd

    def stringify_frame(self, frame_num, dynamic_only=True):
        if frame_num not in self.data['vcd']['frames']:
            warnings.warn("WARNING: Trying to stringify a non-existing frame.")
            return ''

        if dynamic_only:
            return json.dumps(self.data['vcd']['frames'][frame_num])
        else:
            # Need to compose dynamic and static information into a new structure
            # Copy the dynamic info first
            frame_static_dynamic = copy.deepcopy(self.data['vcd']['frames'][frame_num])  # Needs to be a copy!

            # Now the static info for objects, actions, events, contexts and relations
            for element_type in ElementType:
                if element_type.name + 's' in self.data['vcd']['frames'][frame_num]:
                    for uid, content in self.data['vcd']['frames'][frame_num][element_type.name + 's'].items():
                        frame_static_dynamic[element_type.name + 's'][uid].update(
                            self.data['vcd'][element_type.name + 's'][uid]
                        )
                        # Remove frameInterval entry
                        del frame_static_dynamic[element_type.name + 's'][uid]['frame_intervals']

            return json.dumps(frame_static_dynamic)

    def update_object(self, uid, frame_value):
        # This function is only needed if no add_object_data calls are used, but the object needs to be kept alive
        return self.__update_element(ElementType.object, uid, frame_value)

    def update_action(self, uid, frame_value):
        return self.__update_element(ElementType.action, uid, frame_value)

    def update_context(self, uid, frame_value):
        return self.__update_element(ElementType.context, uid, frame_value)

    def update_relation(self, uid, frame_value):
        return self.__update_element(ElementType.relation, uid, frame_value)

    def add_object(self, name, semantic_type='', frame_value=None, uid=None, ont_uid=None, stream=None):
        return self.__add_element(ElementType.object, name, semantic_type, frame_value, uid, ont_uid, stream)

    def add_action(self, name, semantic_type='', frame_value=None, uid=None, ont_uid=None, stream=None):
        return self.__add_element(ElementType.action, name, semantic_type, frame_value, uid, ont_uid, stream)

    def add_event(self, name, semantic_type='', frame_value=None, uid=None, ont_uid=None, stream=None):
        return self.__add_element(ElementType.event, name, semantic_type, frame_value, uid, ont_uid, stream)

    def add_context(self, name, semantic_type='', frame_value=None, uid=None, ont_uid=None, stream=None):
        return self.__add_element(ElementType.context, name, semantic_type, frame_value, uid, ont_uid, stream)

    def add_relation(self, name, semantic_type='', frame_value=None, uid=None, ont_uid=None):
        return self.__add_element(
            ElementType.relation, name, semantic_type, frame_value, uid=uid, ont_uid=ont_uid
        )

    def add_rdf(self, relation_uid, rdf_type, element_uid, element_type):
        assert(isinstance(element_type, ElementType))
        assert(isinstance(rdf_type, RDF))
        if relation_uid not in self.data['vcd']['relations']:
            warnings.warn("WARNING: trying to add RDF to non-existing Relation.")
            return
        else:
            if element_uid not in self.data['vcd'][element_type.name + 's']:
                warnings.warn("WARNING: trying to add RDF using non-existing Element.")
                return
            else:
                if rdf_type == RDF.subject:
                    self.data['vcd']['relations'][relation_uid].setdefault('rdf_subjects', [])
                    self.data['vcd']['relations'][relation_uid]['rdf_subjects'].append(
                        {'uid': element_uid, 'type': element_type.name}
                    )
                else:
                    self.data['vcd']['relations'][relation_uid].setdefault('rdf_objects', [])
                    self.data['vcd']['relations'][relation_uid]['rdf_objects'].append(
                        {'uid': element_uid, 'type': element_type.name}
                    )

    def add_object_data(self, uid, object_data, frame_value=None):
        assert (isinstance(uid, int))

        # 1/3 Update element at vcd (internally, this fuses the frame intervals, etc.
        self.__update_element(ElementType.object, uid, frame_value)

        # 2/3 Update object data
        frame_intervals = utils.as_frame_intervals_array_dict(frame_value)
        self.__update_object_data(uid, object_data, frame_intervals)

        # 3/3 Update auxiliary array
        self.__object_data_names.setdefault(uid, set())
        self.__object_data_names[uid].add(object_data.data['name'])

    ##################################################
    # Get / Read
    ##################################################
    def has(self, element_type, uid):
        if not element_type.name + 's' in self.data['vcd']:
            return False
        else:
            if uid in self.data['vcd'][element_type.name + 's']:
                return True
            else:
                return False

    def get_all(self, element_type):
        """
        Returns all elements of the specified ElementType.
        e.g. all Object's or Context's
        """
        assert(isinstance(element_type, ElementType))
        return self.data['vcd'].get(element_type.name + 's')

    def get_element(self, element_type, uid):
        assert (isinstance(element_type, ElementType))
        if self.data['vcd'].get(element_type.name + 's') is None:
            warnings.warn("WARNING: trying to get a " + element_type.name + " but this VCD has none.")
            return None
        if uid in self.data['vcd'][element_type.name + 's']:
            return self.data['vcd'][element_type.name + 's'][uid]
        else:
            warnings.warn("WARNING: trying to get non-existing " + element_type.name + " with uid: " + str(uid))
            return None

    def get_object(self, uid):
        return self.get_element(ElementType.object, uid)

    def get_action(self, uid):
        return self.get_element(ElementType.action, uid)

    def get_event(self, uid):
        return self.get_element(ElementType.event, uid)

    def get_context(self, uid):
        return self.get_element(ElementType.context, uid)

    def get_relation(self, uid):
        return self.get_element(ElementType.relation, uid)

    def get_frame(self, frame_num):
        assert('frames' in self.data['vcd'])
        return self.data['vcd']['frames'].get(frame_num)

    def get_elements_of_type(self, element_type, type_):
        uids = []
        for uid, element in self.data['vcd'][element_type.name + 's'].items():
            if element['type'] == type_:
                uids.append(uid)
        return uids

    def get_objects_with_object_data_name(self, data_name):
        uids = []
        for uid, object_ in self.data['vcd']['objects'].items():
            if uid in self.__object_data_names:
                if data_name in self.__object_data_names[uid]:
                    uids.append(uid)
        return uids

    def has_frame_object_data_name(self, frame_num, data_name, uid_=-1):
        if frame_num in self.data['vcd']['frames']:
            for uid, obj in self.data['vcd']['frames'][frame_num]['objects'].items():
                if uid_ == -1 or uid == uid_:  # if uid == -1 means we want to loop over all objects
                    for valArray in obj['object_data'].values():
                        for val in valArray:
                            if val['name'] == data_name:
                                return True
        return False

    def get_frames_with_object_data_name(self, uid, data_name):
        frames = []
        if uid in self.data['vcd']['objects'] and uid in self.__object_data_names:
            object_ = self.data['vcd']['objects'][uid]
            if data_name in self.__object_data_names[uid]:
                # Now look into Frames
                fis = object_['frame_intervals']
                for fi in fis:
                    fi_tuple = (fi['frame_start'], fi['frame_end'])
                    for frame_num in range(fi_tuple[0], fi_tuple[1]+1):
                        if self.has_frame_object_data_name(frame_num, data_name, uid):
                            frames.append(frame_num)
        return frames

    def get_object_data(self, uid, data_name, frame_num=None):
        if uid in self.data['vcd']['objects']:
            if data_name in self.__object_data_names[uid]:

                # Frame-specific information
                if frame_num is not None:
                    if uid in self.data['vcd']['frames'][frame_num]['objects']:
                        object__ = self.data['vcd']['frames'][frame_num]['objects'][uid]
                        for valArray in object__['object_data'].values():
                            for val in valArray:
                                if val['name'] == data_name:
                                    return val
                # Static information
                else:
                    object_ = self.data['vcd']['objects'][uid]
                    if "object_data" in object_:
                        for valArray in object_["object_data"].values():
                            for val in valArray:
                                if val['name'] == data_name:
                                    return val
        return {}

    def get_num_elements(self, element_type):
        return len(self.data['vcd'][element_type.name + 's'])

    def get_num_objects(self):
        return self.get_num_elements(ElementType.object)

    def get_num_actions(self):
        return self.get_num_elements(ElementType.action)

    def get_num_events(self):
        return self.get_num_elements(ElementType.event)

    def get_num_contexts(self):
        return self.get_num_elements(ElementType.context)

    def get_num_relations(self):
        return self.get_num_elements(ElementType.relation)

    def get_ontology(self, ont_uid):
        if 'ontologies' in self.data['vcd']:
            if ont_uid in self.data['vcd']['ontologies']:
                return self.data['vcd']['ontologies'][ont_uid]
        return None

    def get_metadata(self):
        if 'metadata' in self.data['vcd']:
            return self.data['vcd']['metadata']
        else:
            return dict()

    def get_frame_intervals(self):
        return self.data['vcd'].get('frame_intervals')

    def get_frame_intervals_of_element(self, element_type, uid):
        assert (element_type.name + 's' in self.data['vcd'])
        return self.data['vcd'][element_type.name + 's'][uid].get('frame_intervals')

    ##################################################
    # Remove
    ##################################################
    def rm_element_by_type(self, element_type, semantic_type):
        elements = self.data['vcd'][element_type.name + 's']
        index = None

        # Get Element from summary
        element = None
        for uid, element in elements.items():
            if element['type'] == semantic_type:
                index = uid
                break

        if index is None:  # not found
            warnings.warn(
                "WARNING: can't remove Element with semantic type: " + str(semantic_type) + ": no Element found",
                Warning
            )
            return

        # Update indexes and other member variables
        uid = index
        if element_type == ElementType.object:
            del self.__object_data_names[uid]

        # Remove from Frames: let's read frameIntervals from summary
        for fi in element['frame_intervals']:
            for frame_num in range(fi['frame_start'], fi['frame_end']+1):
                elements_in_frame = self.data['vcd']['frames'][frame_num][element_type.name + 's']
                if uid in elements_in_frame:
                    del elements_in_frame[uid]
                if not elements_in_frame:  # objects might have end up empty TODO: test this
                    del elements_in_frame

        # Remove from summary
        del elements[uid]

        # Clean-up Frames and Elements
        self.__clean()

    def rm_object_by_type(self, semantic_type):
        self.rm_element_by_type(ElementType.object, semantic_type)

    def rm_action_by_type(self, semantic_type):
        self.rm_element_by_type(ElementType.action, semantic_type)

    def rm_event_by_type(self, semantic_type):
        self.rm_element_by_type(ElementType.event, semantic_type)

    def rm_context_by_type(self, semantic_type):
        self.rm_element_by_type(ElementType.context, semantic_type)

    def rm_relation_by_type(self, semantic_type):
        self.rm_element_by_type(ElementType.relation, semantic_type)

    def rm_element_by_frame(self, element_type, uid, frame_interval_tuple):
        frame_interval_dict = utils.as_frame_interval_dict(frame_interval_tuple)
        elements = self.data['vcd'][element_type.name + 's']

        if uid in elements:
            element = elements[uid]

        else:  # not found
            warnings.warn(
                "WARNING: trying to remove non-existing Element of type: ", element_type.name, " and uid: ", uid
            )
            return

        # Remove from Frames: let's read frameIntervals from summary
        for fi in element['frame_intervals']:
            for frame_num in range(fi['frame_start'], fi['frame_end'] + 1):
                if frame_interval_dict['frame_start'] <= frame_num <= frame_interval_dict['frame_end']:
                    elements_in_frame = self.data['vcd']['frames'][frame_num][element_type.name + 's']
                    if uid in elements_in_frame:
                        del elements_in_frame[uid]
                    if not elements_in_frame:  # objects might have end up empty TODO: test this
                        del elements_in_frame

        # Substract this frameInterval from this element
        self.__remove_element_frame_interval(element_type, uid, frame_interval_dict)

        # Clean-up Frames and Elements
        self.__clean()

        # Update indexes and other member variables
        self.__compute_object_data_names_uid(uid)

        outer_interval = utils.get_outer_frame_interval(element['frame_intervals'])
        if frame_interval_dict['frame_start'] <= outer_interval['frame_start'] \
                and frame_interval_dict['frame_end'] >= outer_interval['frame_end']:
            # The deleted frame interval covers the entire element, so let's delete it from the summary
            del elements[uid]

    def rm_object_by_frame(self, uid, frame_interval_tuple):
        return self.rm_element_by_frame(ElementType.object, uid, frame_interval_tuple)

    def rm_action_by_frame(self, uid, frame_interval_tuple):
        return self.rm_element_by_frame(ElementType.action, uid, frame_interval_tuple)

    def rm_event_by_frame(self, uid, frame_interval_tuple):
        return self.rm_element_by_frame(ElementType.event, uid, frame_interval_tuple)

    def rm_context_by_frame(self, uid, frame_interval_tuple):
        return self.rm_element_by_frame(ElementType.context, uid, frame_interval_tuple)

    def rm_relation_by_frame(self, uid, frame_interval_tuple):
        return self.rm_element_by_frame(ElementType.relation, uid, frame_interval_tuple)

    def rm_element(self, element_type, uid):
        elements = self.data['vcd'][element_type.name + 's']

        # Get Element from summary
        if uid in elements:
            element = elements[uid]

        else:  # not found
            warnings.warn(
                "WARNING: trying to remove non-existing Element of type: ", element_type.name, " and uid: ", uid
            )
            return

        # Update indexes and other member variables
        if element_type == ElementType.object:
            del self.__object_data_names[uid]

        # Remove from Frames: let's read frameIntervals from summary
        for fi in element['frame_intervals']:
            for frame_num in range(fi['frame_start'], fi['frame_end']+1):
                elements_in_frame = self.data['vcd']['frames'][frame_num][element_type.name + 's']
                if uid in elements_in_frame:
                    del elements_in_frame[uid]
                if not elements_in_frame:  # objects might have end up empty TODO: test this
                    del elements_in_frame

        # Clean-up Frames
        self.__clean()

        # Delete this element from summary
        del elements[uid]

    def rm_object(self, uid):
        self.rm_element(ElementType.object, uid)

    def rm_action(self, uid):
        self.rm_element(ElementType.action, uid)

    def rm_event(self, uid):
        self.rm_element(ElementType.event, uid)

    def rm_context(self, uid):
        self.rm_element(ElementType.context, uid)

    def rm_relation(self, uid):
        self.rm_element(ElementType.relation, uid)