git ls-files | Where-Object { $_ -like '*.rs' } | ForEach-Object { (Get-Content $_).Count } | Measure-Object -Sum | Select-Object -ExpandProperty Sum
