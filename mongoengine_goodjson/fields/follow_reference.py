#!/usr/bin/env python
# coding=utf-8

"""Follow Reference Field code."""

import logging

from bson import SON
import mongoengine as db
from ..document import Document

log = logging.getLogger(__name__)


class FollowReferenceField(db.ReferenceField):
    """
    Follow Reference Field.

    This field can be treated as a field like ReferenceField, but generates
    the JSON/dict of the referenced document like embedded document.

    Note:
        This field doesn't check recursion level. Therefore, please be careful
        for self-referenced document.
    """

    def __init__(self, *args, **kwargs):
        """
        Initialize the class.

        Parameters:
            *args, **kwsrgs: Any arguments to be passed to ReferenceField.
        Keyword Arguments:
            id_check: Set False to disable id check. By default, this value is
                True
            autosave: Set True to save/update the referenced document when
                to_python is called.
            max_depth: Set natural value to set depath limit for
                loop-reference. By default this value is set to 3.

        """
        self.id_check = kwargs.pop("id_check", True)
        self.autosave = kwargs.pop("autosave", False)
        self.max_depth = kwargs.pop("max_depth", None) or 3
        super(FollowReferenceField, self).__init__(*args, **kwargs)
        if self.max_depth < 0 and self.document_type_obj is \
                db.fields.RECURSIVE_REFERENCE_CONSTANT:
            log.warn(
                "[BE CAREFUL!] Unlimited self reference might cause "
                "infinity loop! [BE CAREFUL!]"
            )

    def to_mongo(self, document, **kwargs):
        """
        Convert to python-typed dict.

        Parameters:
            document: The document.

        """
        cur_depth = self.max_depth
        try:
            cur_depth = getattr(self, "$$cur_depth$$")
            if self.max_depth > -1 and cur_depth >= self.max_depth:
                raise AttributeError()
        except AttributeError:
            return super(
                FollowReferenceField, self
            ).to_mongo(document, **kwargs)
        doc = document
        if isinstance(document, db.Document):
            if document.pk is None and self.id_check:
                self.error("The referenced document needs ID.")
        else:
            doc = self.document_type.objects(
                pk=super(
                    FollowReferenceField, self
                ).to_mongo(document, **kwargs)
            ).get()
        ret = doc.to_mongo(
            cur_depth=cur_depth + 1, good_json=True, **kwargs
        ) if isinstance(doc, Document) else doc.to_mongo(**kwargs)
        if "_id" in ret and issubclass(self.document_type, Document):
            ret["id"] = ret.pop("_id", None)
        return ret

    def to_python(self, value):
        """
        Convert to python-based object.

        Parameters:
            value: The python-typed document.

        """
        clone = value
        if isinstance(value, dict):
            clone = self.document_type._from_son(
                SON(value), created="id" not in value
            )
            if self.autosave:
                clone.save()
        ret = super(FollowReferenceField, self).to_python(clone)
        return ret
