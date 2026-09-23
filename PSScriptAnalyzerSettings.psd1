@{
    # The scripts are interactive lab tools that print colored progress for learners, so Write-Host
    # is intentional. Data that other tools consume is written to stdout with -Json instead.
    ExcludeRules = @(
        'PSAvoidUsingWriteHost'
    )
    Severity     = @('Error', 'Warning')
}
