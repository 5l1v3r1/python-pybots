# -*- coding: UTF-8 -*-
"""Classes and functions related to hashing.

The following classes and functions allow to build hash lookup tables from text
 dicitonaries.

"""


__all__ = ["LookupTable"]


class LookupTable(object):
    """
    Lookup table class for password cracking.

    :param dictionary:  the dictionary file to be loaded
    :param algorithm:   the hash algorithm to be used
    :param ratio:       ratio of value to be hashed in the lookup table (by
                         default, every value is considered but, i.e. with a
                         big wordlist, it can be better to use a ratio of
                         2/3/4/5/... in order to limit the memory load)
    :param dict_filter: function aimed to filter the words from the dictionary
                         (e.g. only alpha-numeric)
    :param verbose:     logging verbosity
    :param logger:      logging instance
    """
    def __init__(self, dictionary, algorithm="md5", ratio=1,
                 dict_filter=None, verbose=True, logger=None):
        if not os.path.isfile(dictionary):
            raise ValueError("Bad dictionary file")
        if algorithm not in ["md5", "sha1", "sha256"]:
            raise ValueError("Bad hashing algorithm")
        if not isinstance(ratio, float) or 0 >= ratio > 1:
            raise ValueError("Bad ratio")
        self.logger = logger
        self.verbose = verbose
        algorithm = eval(algorithm)
        self.__lookup = {}
        self.__log("Making the lookup table ; this may take a while...")
        with open(dictionary) as f:
            filtered = 0
            m = round(1 / float(ratio))
            for i, l in enumerate(f):
                if (i - filtered) % m == 0:
                    l = l.strip()
                    if hasattr(dict_filter, '__call__') and dict_filter(l):
                        self.__lookup[algorithm(l)] = l
                    else:
                        filtered += 1
        self.__log("Lookup table ready !")

    def __log(self, msg):
        if self.verbose:
            if self.logger is None:
                print(msg)
            else:
                self.logger.info(msg)

    def get(self, h):
        """
        Cracking public method.

        :param h: input hash
        :return: corresponding value
        """
        try:
            return self.__lookup[h]
        except KeyError:
            return ""
