# This assumes the default CIDOC-CRM, even though the model code
# can generate classes for any ontology

import os
import json

from .model import (
    Identifier,
    Mark,
    HumanMadeObject,
    Type,
    Person,
    Material,
    MeasurementUnit,
    Place,
    Dimension,
    Currency,
    ConceptualObject,
    TimeSpan,
    Actor,
    PhysicalThing,
    Language,
    LinguisticObject,
    InformationObject,
    Formation,
    Dissolution,
    Activity,
    Group,
    Name,
    MonetaryAmount,
    Right,
    Encounter,
    Destruction,
    AttributeAssignment,
    BaseResource,
    PhysicalObject,
    Acquisition,
    HumanMadeFeature,
    VisualItem,
    Set,
    Birth,
    Death,
    PropositionalObject,
    Payment,
    Creation,
    Period,
    Production,
    Event,
    DigitalObject,
    TransferOfCustody,
    Move,
    DigitalService,
    CRMEntity,
    STR_TYPES,
    factory,
    ExternalResource,
)


# Add classified_as initialization hack for all resources
def post_init(self, **kw):
    if self.__class__._classification:
        for t in self._classification:
            self.classified_as = t


BaseResource._post_init = post_init

instances = {}
instance_types = {}


def register_vocab_class(name, data):
    parent = data["parent"]
    id = data["id"]
    label = data["label"]
    vocab = data.get("vocab", "aat")

    # We've imported them above...
    parent = globals()[parent]

    c = type(name, (parent,), {})
    if id.startswith("http"):
        t = Type(id)
    else:
        t = Type("http://vocab.getty.edu/%s/%s" % (vocab, id))
    t._label = label
    instance_types[name] = t
    c._classification = [t]
    if "metatype" in data:
        t.classified_as = instances[data["metatype"]]
    c._type = None  # To avoid conflicting with parent class
    globals()[name] = c
    return c


def register_instance(name, data):
    parent = data["parent"]
    id = data["id"]
    vocab = data.get("vocab", "aat")
    label = data["label"]

    parent = globals()[parent]

    if id.startswith("http"):
        t = parent(id)
    else:
        t = parent("http://vocab.getty.edu/%s/%s" % (vocab, id))
    t._label = label
    instances[name] = t
    return t


# Consider:
# pen, pencil, card, cardboard, porcelain, wax, ceramic, plaster
# crayon, millboard, gouache, brass, stone, lead, iron, clay,
# alabaster, limestone

# Read in external files from data/ directory
dd = os.path.join(os.path.dirname(__file__), "data")
cls_fn = os.path.join(dd, "vocab_classes.json")
inst_fn = os.path.join(dd, "vocab_instances.json")

fh = open(cls_fn)
cls_data = fh.read()
fh.close()
fh = open(inst_fn)
inst_data = fh.read()
fh.close()

cls_js = json.loads(cls_data)
inst_js = json.loads(inst_data)

for name, v in inst_js.items():
    if "parent" in v and not v["parent"] in cls_js:
        register_instance(name, v)
for name, v in cls_js.items():
    if "parent" in v:
        register_vocab_class(name, v)
for name, v in inst_js.items():
    if "parent" in v and v["parent"] in cls_js:
        register_instance(name, v)


def add_classification(obj, cl_type):
    c = cl_type()
    for cn in c._classification:
        if hasattr(obj, "classified_as") and not cn in obj.classified_as:
            obj.classified_as = cn
        elif not hasattr(obj, "classified_as"):
            obj.classified_as = cn
    return obj


def make_multitype_obj(*args, **kw):
    # (class1, class2, class3, name=foo, other=bar)
    inst = args[0](**kw)
    for c in args[1:]:
        for cn in c._classification:
            if hasattr(inst, "classified_as") and not cn in inst.classified_as:
                inst.classified_as = cn
            elif not hasattr(inst, "classified_as"):
                inst.classified_as = cn
    return inst


def conceptual_only_parts():
    # Make .part work as expected for Right
    # which is only propositional and not symbolic, so P148 not P106

    def set_conceptual_part(self, value):
        self.conceptual_part = value

    def set_conceptually_part_of(self, value):
        self.conceptually_part_of = value

    def rights_getter(self, what):
        if what == "part":
            return self.conceptual_part
        elif what == "part_of":
            return self.conceptually_part_of
        else:
            object.__getattr__(self, what)

    Right.set_part = set_conceptual_part
    Right.set_part_of = set_conceptually_part_of
    Right._property_name_map["conceptual_part"] = "part"
    Right._property_name_map["conceptually_part_of"] = "part_of"
    Right._all_properties["part"] = PropositionalObject._all_properties["conceptual_part"]
    Right._all_properties["part_of"] = PropositionalObject._all_properties["conceptually_part_of"]
    Right.__getattr__ = rights_getter


def add_art_setter():
    # Linked.Art profile requires aat:300133025 on all artworks
    # Art can be a HumanMadeObject or an InformationObject
    # set it by adding art=1 to the constructor

    def art_post_init(self, **kw):
        super(HumanMadeObject, self)._post_init(**kw)
        if "art" in kw:
            self.classified_as = instances["artwork"]

    HumanMadeObject._post_init = art_post_init

    def art2_post_init(self, **kw):
        if "art" in kw:
            self.classified_as = instances["artwork"]
        super(InformationObject, self)._post_init(**kw)

    InformationObject._post_init = art2_post_init


def add_attribute_assignment_check():
    # Allow references to properties in p177 on AttrAssign
    # Validate that the property is allowed in assigned
    # either on set, or when assigned is set

    p177 = factory.context_rev.get("crm:P177_assigned_property", "assigned_property")
    ass = factory.context_rev.get("crm:P141_assigned", "assigned")
    assto = factory.context_rev.get("crm:P140:assigned_attribute_to", "assigned_to")

    def aa_set_assigned(self, value):
        assto_res = getattr(self, assto, None)
        if assto_res:
            p177_res = getattr(self, p177, None)
            assto_res._check_prop(p177_res, value)

        current = getattr(self, ass, None)
        if current:
            value = [*current, value]
        elif type(value) is not list:
            value = [value]
        object.__setattr__(self, ass, value)

    setattr(AttributeAssignment, "set_%s" % ass, aa_set_assigned)

    def aa_set_assigned_to(self, value):
        ass_res = getattr(self, ass, None)
        p177_res = getattr(self, p177, None)
        if ass_res and p177_res:
            # unmap the URI to property name
            for ar in ass_res:
                value._check_prop(p177_res, ar)
        object.__setattr__(self, assto, value)

    setattr(AttributeAssignment, "set_%s" % assto, aa_set_assigned_to)

    def aa_set_assigned_property_type(self, value):
        ass_res = getattr(self, ass, None)
        assto_res = getattr(self, assto, None)
        if ass_res and assto_res:
            for ar in ass_res:
                assto_res._check_prop(value, ar)
        object.__setattr__(self, p177, value)

    setattr(AttributeAssignment, "set_%s" % p177, aa_set_assigned_property_type)


def add_linked_art_boundary_check():
    boundary_classes = [
        x.__name__
        for x in [
            Actor,
            HumanMadeObject,
            Person,
            Group,
            VisualItem,
            Place,
            Period,
            LinguisticObject,
            PropositionalObject,
            Set,
            Event,
            DigitalObject,
            DigitalService,
        ]
    ]
    data_embed_classes = [Name, Identifier, Dimension, TimeSpan, MonetaryAmount]
    type_embed_classes = [Type, Currency, Language, Material, MeasurementUnit]
    event_embed_classes = [Birth, Creation, Production, Formation, Payment, Death, Destruction, Dissolution]
    all_embed_classes = []
    all_embed_classes.extend(data_embed_classes)
    all_embed_classes.extend(type_embed_classes)
    all_embed_classes.extend(event_embed_classes)
    embed_classes = [x.__name__ for x in all_embed_classes]

    # Activity, AttributeAssignment, InformationObject, TransferOfCustody, Move
    # Propositional Object

    ExternalResource._embed_override = None

    def my_linked_art_boundary_check(self, top, rel, value):
        # True = Embed ; False = Split
        if value._embed_override is not None:
            return value._embed_override
        elif isinstance(value, LinguisticObject) and hasattr(value, "classified_as"):
            for ca in value.classified_as:
                if instances["brief text"] in getattr(ca, "classified_as", []):
                    return True
        # Non Statement Linguistic objects might still be internal or external
        # so apply logic from relating properties, not return False
        elif isinstance(value, ProvenanceEntry):
            return False

        boundary_crossing_props = set(
            [
                "part_of",
                "member_of",
                "specific_purpose",
                "caused_by",
                "starts_before_the_end_of",
                "ends_after_the_start_of",
                "starts_before_the_start_of",
                "starts_after_the_start_of",
                "ends_before_the_start_of",
                "starts_after_the_end_of",
                "ends_before_the_end_of",
                "ends_after_the_end_of",
            ]
        )

        if rel in ["part", "member", "specific_purpose_of", "caused"]:
            # Downwards, internal simple partitioning
            # This catches an internal part to a LinguisticObject
            return True
        elif rel in boundary_crossing_props:
            # upwards partition refs are inclusion, and always boundary crossing
            return False
        elif value.type in boundary_classes:
            # This catches the external text LinguisticObject
            return False
        elif value.type in embed_classes:
            return True
        else:
            # Default to embedding to avoid data loss
            return True

    setattr(BaseResource, "_linked_art_boundary_okay", my_linked_art_boundary_check)
    factory.linked_art_boundaries = True


def set_linked_art_uri_segments():
    HumanMadeObject._uri_segment = "object"
    Activity._uri_segment = "event"
    Event._uri_segment = "event"
    Period._uri_segment = "event"
    Place._uri_segment = "place"
    InformationObject._uri_segment = "info"
    Group._uri_segment = "group"
    # Actor._uri_segment = "actor"
    Person._uri_segment = "person"
    PhysicalObject._uri_segment = "object"
    LinguisticObject._uri_segment = "text"
    PropositionalObject._uri_segment = "concept"
    DigitalObject._uri_segment = "digital"
    DigitalService._uri_segment = "digital"
    Type._uri_segment = "concept"
    Language._uri_segment = "concept"
    MeasurementUnit._uri_segment = "concept"
    Currency._uri_segment = "concept"
    Material._uri_segment = "concept"
    VisualItem._uri_segment = "visual"
    ProvenanceEntry._uri_segment = "provenance"
    Exhibition._uri_segment = "activity"
    Set._uri_segment = "set"


def add_helper_functions():
    # Add filter functions to the right bits of the model

    def get_names(self, filter=None):
        return [x for x in self.identified_by if isinstance(x, Name) and (not filter or filter in x.classified_as)]

    def get_identifiers(self, filter=None):
        return [x for x in self.identified_by if isinstance(x, Identifier) and (not filter or filter in x.classified_as)]

    def get_statements(self, filter=None):
        return [
            x
            for x in self.referred_to_by
            if isinstance(x, LinguisticObject) and x.content and (not filter or filter in x.classified_as)
        ]

    CRMEntity.get_names = get_names
    CRMEntity.get_identifiers = get_identifiers
    CRMEntity.get_statements = get_statements
