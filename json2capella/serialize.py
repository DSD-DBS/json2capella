# Copyright DB InfraGO AG and contributors
# SPDX-License-Identifier: Apache-2.0
"""Serialize to Capella data package."""

import logging
import typing as t

import capellambse
from capellambse.model.crosslayer import information

from json2capella import parse

logger = logging.getLogger(__name__)


class CapellaDataPackage:
    """Capella data package wrapper."""

    def __init__(self, capella_path: str, layer: str):
        self.model = capellambse.MelodyModel(capella_path)
        self.data_package = getattr(self.model, layer).data_package
        self.data_types = self.model.sa.data_package.packages.create(
            "DataPkg", name="Data Types"
        )

    def remove_class(
        self, cls_obj: information.Class, remove_from: information.DataPkg
    ):
        """Remove class from Capella package."""
        try:
            remove_from.classes.remove(cls_obj)
            logger.info("%s deleted.", cls_obj._short_repr_())
        except ValueError:
            pass

    def remove_package(
        self, pkg_obj: information.DataPkg, remove_from: information.DataPkg
    ):
        """Remove package from Capella package."""
        try:
            remove_from.packages.remove(pkg_obj)
            logger.info("%s deleted.", pkg_obj._short_repr_())
        except ValueError:
            pass

    def remove_enum(
        self,
        enum_obj: information.datatype.Enumeration,
        remove_from: information.DataPkg,
    ):
        """Remove enum from Capella package."""
        try:
            remove_from.datatypes.remove(enum_obj)
            logger.info("%s deleted.", enum_obj._short_repr_())
        except ValueError:
            pass

    def create_package(
        self, pkg_def: parse.PkgDef, create_in: information.DataPkg
    ) -> information.DataPkg | None:
        """Create package in Capella package.

        Returns
        -------
            Package object if package already exists, else None.
        """
        try:
            pkg_obj = create_in.packages.by_name(pkg_def.name)
            logger.info("%s already exists.", pkg_obj._short_repr_())
            return pkg_obj
        except KeyError:
            pkg_obj = create_in.packages.create(
                name=pkg_def.name, description=pkg_def.description
            )
            logger.info("%s created.", pkg_obj._short_repr_())
            return None

    def create_class(
        self,
        cls_def: parse.ClassDef,
        create_in: information.DataPkg,
    ) -> information.Class | None:
        """Create class in Capella package.

        Returns
        -------
            Class object if class already exists, else None.
        """
        try:
            cls_obj = create_in.classes.by_name(cls_def.name)
            logger.info("%s already exists.", cls_obj._short_repr_())
            return cls_obj
        except KeyError:
            cls_obj = create_in.classes.create(
                name=cls_def.name, description=cls_def.description
            )
            logger.info("%s created.", cls_obj._short_repr_())
            return None

    def create_enum(
        self, enum: parse.EnumDef, create_in: information.DataPkg
    ) -> information.datatype.Enumeration | None:
        """Create enum in Capella package.

        Returns
        -------
            Enumeration object if enumeration already exists, else None.
        """
        try:
            enum_obj = self.model.search(
                "Enumeration", below=create_in
            ).by_name(enum.name)
            logger.info("%s already exists.", enum_obj._short_repr_())
            return enum_obj
        except KeyError:
            enum_obj = create_in.datatypes.create(
                "Enumeration", name=enum.name, description=enum.description
            )
            for literal in enum.literals:
                literal_obj = enum_obj.owned_literals.create(
                    "EnumerationLiteral",
                    name=literal.name,
                    description=literal.description,
                )
                literal_obj.value = capellambse.new_object(
                    "LiteralNumericValue",
                    value=str(literal.value),
                )
            logger.info("%s created.", enum_obj._short_repr_())
            return None

    def create_properties(
        self, class_def: parse.ClassDef, create_in: information.DataPkg
    ) -> None:
        """Create properties for Capella class."""
        superclass = create_in.classes.by_name(class_def.name)

        for prop in class_def.properties:
            if isinstance(prop.type, parse.ClassDef):
                partclass = self.model.search(
                    "Class", below=create_in
                ).by_name(prop.type.name)
                composition = self._create_composition(
                    superclass, prop, partclass
                )
                association = create_in.owned_associations.create(
                    navigable_members=[composition]
                )
                association.members.create(
                    "Property",
                    type=superclass,
                    kind="ASSOCIATION",
                    min_card=capellambse.new_object(
                        "LiteralNumericValue", value="1"
                    ),
                    max_card=capellambse.new_object(
                        "LiteralNumericValue", value="1"
                    ),
                )
            else:
                if isinstance(prop.type, parse.EnumDef):
                    property_type = self.model.search(
                        "Enumeration", below=create_in
                    ).by_name(prop.type.name)
                else:
                    try:
                        property_type = self.data_types.datatypes.by_name(
                            prop.type
                        )
                    except KeyError:
                        if "char" in prop.type or "string" in prop.type:
                            type = "StringType"
                        elif "bool" in prop.type or "boolean" in prop.type:
                            type = "BooleanType"
                        else:
                            type = "NumericType"

                        property_type = self.data_types.datatypes.create(
                            type, name=prop.type
                        )

                composition = self._create_composition(
                    superclass, prop, property_type
                )
            self._set_cardinality(composition, prop)
            self._set_range(composition, prop)
        logger.info("Created properties for %s.", class_def.name)

    def _create_composition(
        self,
        superclass: information.Class,
        prop_def: parse.PropertyDef,
        property_type: (
            information.Class | t.Type[information.datatype.DataType]
        ),
    ) -> information.Property:
        """Create composition for Capella class."""
        try:
            overlap = superclass.owned_properties.by_name(prop_def.name)
            superclass.owned_properties.remove(overlap)
        except KeyError:
            pass
        composition = superclass.owned_properties.create(
            name=prop_def.name,
            type=property_type,
            kind="COMPOSITION",
            description=prop_def.description,
        )
        return composition

    def _set_cardinality(
        self, composition: information.Property, prop: parse.PropertyDef
    ) -> None:
        """Set cardinality for composition in Capella model."""
        composition.min_card = capellambse.new_object(
            "LiteralNumericValue", value=prop.min_card
        )
        composition.max_card = capellambse.new_object(
            "LiteralNumericValue", value=prop.max_card
        )

    def _set_range(
        self, composition: information.Property, prop: parse.PropertyDef
    ) -> None:
        """Set range for composition in Capella model."""
        if prop.min_value:
            composition.min = capellambse.new_object(
                "LiteralNumericValue", value=prop.min_value
            )
        if prop.max_value:
            composition.max = capellambse.new_object(
                "LiteralNumericValue", value=prop.max_value
            )

    def save_changes(self) -> None:
        """Save changes to Capella model."""
        self.model.save()
