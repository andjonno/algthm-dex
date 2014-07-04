"""
Model encapsulates all information obtained through indexing. This model will be validated prior to database insertion.
Anything abnormal shall be reported.

The model is not a base_model extension, it is not uniformly related to one database table. The model however, contains
smaller subsets which each are base_models. The IndexResult is simply to encapsulate such models and provide a single
point for moving around results and validation operations.
"""

class IndexResult(object):
    pass