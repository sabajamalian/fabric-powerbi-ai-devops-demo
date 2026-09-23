# TMDL cheat sheet

The code blocks below are indented with real tabs, the way TMDL requires.

## Table with a marked date column and a hierarchy

```tmdl
/// Calendar of every day from 1 Jan 2024 to 31 Dec 2025. Use for all time analysis.
table Date
	dataCategory: Time

	/// Calendar date. Key of the Date table; relate fact dates to this column.
	column Date
		dataType: dateTime
		isKey
		formatString: yyyy-mm-dd
		summarizeBy: none
		sourceColumn: cal_dt

	/// Month name, January to December. Sorted by Month Number.
	column Month
		dataType: string
		summarizeBy: none
		sourceColumn: mth_nm
		sortByColumn: 'Month Number'

	hierarchy Calendar

		level Year
			column: Year

		level 'Year Month'
			column: 'Year Month'
```

## Default label

```tmdl
	/// Store name, for example Riverbend. Default label for a store.
	column 'Store Name'
		dataType: string
		isDefaultLabel
		summarizeBy: none
		sourceColumn: store_nm
```

## Calculated column

```tmdl
	/// New or Refill, decoded from Fill Type Code. Use for new versus refill analysis.
	column 'Fill Type' = IF('Prescription Fill'[Fill Type Code] = "N", "New", "Refill")
		dataType: string
		summarizeBy: none
```

## Measure

```tmdl
	/// Month-over-month percent change in Prescriptions Filled.
	measure 'MoM %' = DIVIDE([MoM Change], [Prescriptions Filled PM])
		formatString: +0.0%;-0.0%;0.0%
		displayFolder: Time Comparison
```

## Relationship

Many-to-one from the fact table to a dimension, single direction (the default, so no `crossFilteringBehavior` line):

```tmdl
relationship 'Prescription Fill to Medication'
	fromColumn: 'Prescription Fill'.'Medication Key'
	toColumn: Medication.'Medication Key'
```

A date relationship also sets `joinOnDateBehavior: datePartOnly`.

## Turn off auto date/time

In `model.tmdl`:

```tmdl
annotation __PBI_TimeIntelligenceEnabled = 0
```

## Lint codes

| Code | Severity | Meaning |
|---|---|---|
| TMDL001 | error | Spaces used for indentation |
| TMDL002 | error | Unclosed ```` ``` ```` expression block |
| TMDL003 | error | `//` comment; TMDL only has `///` descriptions |
| TMDL004 | warning | `///` description not directly above an object |
| TMDL005 | error | Property outside any object |
| TMDL010 | error | Missing `definition` folder |
| TMDL011 | error | Table declared twice |
| TMDL012 | error | `ref table` with no table file |
| TMDL013 | error | Table file not listed in `model.tmdl` |
| TMDL014 | error | Two columns or measures in one table share a name |
| TMDL015 | error | `sortByColumn` points to a column that doesn't exist |
| TMDL016 | error | Column has no `dataType` |
| TMDL017 | error | Hierarchy level points to a missing column |
| TMDL018 | warning | Table has no partition |
| TMDL020 | warning | Description over 200 characters |
| TMDL021 | warning | Measure has no `formatString` |
| TMDL030 to TMDL032 | error | DAX refers to an unknown table, column, or measure |
| TMDL040 to TMDL042 | error | Relationship missing a property, or using an unknown table or column |
