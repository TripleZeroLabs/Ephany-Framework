# BIM Integration and Units

Ephany is built for interoperability with Building Information Modeling
workflows. This page covers how asset attributes carry unit information, how
that maps onto Autodesk's type system, and how values are converted on the way
in and out of the API.

## Unit-aware custom fields

`AssetAttribute` is a schema registry for the open-ended `custom_fields` JSON
on every Asset. It lets the catalog carry an unbounded set of properties —
`flange_rating`, `voltage`, `material_finish` — without a database migration
for each one, while still enforcing a type per field.

Each attribute declares a `unit_type`, and that is what makes conversion
possible.

## Automatic unit conversion

**Storage is always base metric.** Millimetres for length, kilograms for mass,
square metres for area. One representation in the database means values are
directly comparable across a fleet regardless of who entered them.

**Input and output follow the user.** Conversion happens in the serializer
layer — see `UnitConverter` in [`ephany_framework/utils.py`](../ephany_framework/utils.py)
and its use in [`assets/serializers.py`](../assets/serializers.py) — driven by
the requesting user's `UserSettings`.

So a user whose `length_unit` is inches can PATCH `shelf_width: 10`, the
database stores `254.0`, and a read by that same user returns `10.0`. A
colleague working in millimetres reads `254.0` from the same record.

> This applies to user-authenticated requests, which is where `UserSettings`
> comes from. A request authenticated with an API key has no user behind it and
> therefore no unit preference — those read and write base metric directly.

## Autodesk ForgeTypeId mapping

`AssetAttribute.UnitType` values are Autodesk ForgeTypeId schema strings, not
an internal enum:

| Unit type | ForgeTypeId |
| --- | --- |
| Length | `autodesk.spec.aec:length-2.0.0` |
| Distance | `autodesk.spec.aec:distance-1.0.0` |
| Area | `autodesk.spec.aec:area-2.0.0` |
| Volume | `autodesk.spec.aec:volume-2.0.0` |
| Mass / Weight | `autodesk.spec.aec:mass-2.0.0` |
| Density | `autodesk.spec.aec:massDensity-2.0.0` |
| Angle | `autodesk.spec.aec:angle-2.0.0` |
| Slope | `autodesk.spec.aec:slope-2.0.0` |
| Number (unitless) | `autodesk.spec.aec:number-2.0.0` |

Storing the ForgeTypeId itself means data pulled from Ephany can go straight
into Revit or the Forge APIs without a translation table in between — the
identifier the receiving system expects is already the value in the field.

* [Autodesk ForgeTypeId documentation](https://www.revitapidocs.com/2024/e895e206-7654-445f-27a7-669df676df21.htm)

## Roadmap

Deeper BIM integration under consideration:

* **Revit built-in parameters** — direct mapping to Revit's standard hardcoded
  parameters.
  ([docs](https://www.revitapidocs.com/2024/fb011c91-be7e-f737-28c7-3f1e1917a0e0.htm))
* **Shared parameters** — loading GUID-based shared parameter files (`.txt`) so
  definitions stay consistent across projects.
  ([docs](https://help.autodesk.com/view/RVT/2024/ENU/?guid=GUID-91270D94-D66A-4973-8AB6-CB697424992A))
* **IFC property sets** — IFC4/IFC2x3 property sets such as `Pset_WallCommon`
  for OpenBIM exports.
  ([buildingSMART](https://standards.buildingsmart.org/IFC/RELEASE/IFC4/ADD2_TC1/HTML/))

## Attaching BIM files to an asset

`AssetFile` carries the artefacts themselves, categorised by type — `RFA` for a
Revit family, `DWG` for CAD, `PDS` for a cut sheet. Files attach to the catalog
Asset rather than to a project instance, so one family definition serves every
site where that asset appears.
