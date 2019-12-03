az login

$subscriptionName = "<your subscription here>"
az account set -s $subscriptionName

$env:CLI_DEBUG=0

$rg = "<your resource group name"
$location = "<your azure location/region>"
az group create -n $rg -l $location

$cosmosAccountName = "cbreweatherdemo2"
$cosmosAccount = (az cosmosdb create --name $cosmosAccountName --resource-group $rg --default-consistency-level "Session" --enable-automatic-failover false) | ConvertFrom-Json
$cosmosKey = (az cosmosdb keys list --name $cosmosAccountName --resource-group $rg --query 'primaryMasterKey')
$databaseName = "weatherappdb"
az cosmosdb sql database create --account-name $cosmosAccountName --name $databaseName --resource-group $rg --throughput 800
$buildingsCollName = "buildings"
az cosmosdb sql container create --account-name $cosmosAccountName --database-name $databaseName --resource-group $rg --throughput 800 `
    --name $buildingsCollName --partition-key-path "/City" 
az cosmosdb sql container create --account-name $cosmosAccountName --database-name $databaseName --resource-group $rg --throughput 800 `
    --name "alerts" --partition-key-path "/areaId" --ttl 18000
az cosmosdb sql container create --account-name $cosmosAccountName --database-name $databaseName --resource-group $rg --throughput 800 `
    --name "recommendations" --partition-key-path "/alertType"
    

$stgacctName = "weatherappnotifacct2"
$stgAcct = (az storage account create --name $stgacctName --location $location --resource-group $rg --sku Standard_LRS) | ConvertFrom-Json
$queueName = "outbound-email"
$storageKey = (az storage account keys list -n $stgacctName -g $rg --query "[0].value")
az storage queue create --name $queueName --account-name $stgacctName --account-key $storageKey


$appsvcplanName = "WeatherAppSvcPlan2"
$appsvcplan = (az appservice plan create --name $appsvcplanName --is-linux --location $location --sku B1 --resource-group $rg) | ConvertFrom-Json

$funcname = "WeatherAppNotificationFunc2"
#az functionapp create --resource-group $rg --consumption-plan-location $location --name $funcname --storage-account $stgacctName --runtime Python --os-type Linux --runtime-version 3.7
az functionapp create --resource-group $rg --plan $appsvcplanName --name $funcname --storage-account $stgacctName --runtime python --os-type linux --runtime-version 3.7

func azure functionapp publish $funcname
$cosmosUriSetting = 'COSMOS_ACCOUNT_URI="' + $cosmosAccount.documentEndpoint + '"'
$cosmosKeySetting = 'COSMOS_ACCOUNT_KEY=' + $cosmosKey 
$cosmosDBID = 'COSMOS_DB_ID="' + $databaseName + '"'
$collSetting = 'COSMOS_BUILDINGS_COLL="' + $buildingsCollName + '"'
$queueAccountSetting = 'QUEUE_STORAGE_ACCOUNT="' + $stgAcct.primaryEndpoints.queue + '"'
$queueNameSetting = 'QUEUE_NAME="' + $queueName + '"'
$queueStorageKeySetting = 'QUEUE_STORAGE_KEY="' + $storageKey + '"'
az functionapp config appsettings set --name $funcname --resource-group $rg --settings `
    'WEATHER_API_KEY="<your api key here>"' `
    'WEATHER_API_ENDPOINT="https://api.weather.com"' `
    'WEATHER_ADMIN_CODE="ON:CA"' `
    $cosmosUriSetting `
    $cosmosKeySetting `
    $cosmosDBID `
    $collSetting `
    $queueAccountSetting `
    $queueNameSetting `
    $queueStorageKeySetting


