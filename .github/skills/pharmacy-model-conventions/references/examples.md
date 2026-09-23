# Before and after examples

## Column name and description

Before:

```tmdl
	column proc_mins
		dataType: int64
		formatString: 0
		summarizeBy: sum
		sourceColumn: proc_mins
```

After:

```tmdl
	/// Minutes from intake to ready for pickup for this fill. Average it; never sum it.
	column 'Processing Time (min)'
		dataType: int64
		formatString: 0.0
		summarizeBy: average
		sourceColumn: proc_mins
```

The `sourceColumn` still says `proc_mins`, because that's the CSV header.

## Hidden key

```tmdl
	/// Surrogate key that links fills to Store. Hidden; use Store Name or Store Code instead.
	column 'Store Key'
		dataType: int64
		isHidden
		formatString: 0
		summarizeBy: none
		sourceColumn: store_key
```

## Measure

```tmdl
	/// Refill Rate divided by the chain-wide Refill Rate for the same period. 1.00 is the chain average.
	measure 'Refill Rate Index vs Chain' = DIVIDE([Refill Rate], CALCULATE([Refill Rate], REMOVEFILTERS('Store')))
		formatString: 0.00
		displayFolder: Refills
```

## Weak and strong descriptions

| Weak | Strong |
|---|---|
| The region. | Sales region of the store: North, South, East, or West. |
| Count of fills. | Number of prescription fills, new and refill. The standard volume measure; also called fills or scripts. |
| Store table. | One row per Contoso Pharmacy store (12 stores in 4 regions). Use Store Name to label stores. |
