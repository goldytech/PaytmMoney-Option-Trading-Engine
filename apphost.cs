#:sdk Aspire.AppHost.Sdk@13.1.0
#:package Aspire.Hosting.Python@13.1.0
#:package Aspire.Hosting.Redis@13.1.0
#:package CommunityToolkit.Aspire.Hosting.Python.Extensions@13.1.2-beta.506

using Aspire.Hosting.Python;

var builder = DistributedApplication.CreateBuilder(args);

var publicAccessToken = builder.AddParameter("publicAccessToken",secret: true);
var redisCache = builder.AddRedis("cache")
    .WithRedisInsight()
    .WithDataVolume(isReadOnly: false)
    .WithPersistence(interval: TimeSpan.FromMinutes(5),keysChangedThreshold: 100);

builder.AddPythonApp("py-app", "py-app", "main.py")
    .WithUv()
    .WithReference(redisCache)
    .WaitFor(redisCache)
    // .WithOtlpExporter()
    .WithEnvironment("PUBLIC_ACCESS_TOKEN", publicAccessToken)
    .WithEnvironment("MARKET_DATA_TTL_SECONDS", "300")
    .WithEnvironment("MARKET_DATA_MAX_SNAPSHOTS", "25")
    .WithEnvironment("MARKET_DATA_SCAN_BATCH_SIZE", "200")
    .WithEnvironment("MARKET_DATA_KEY_PREFIX", "market");


builder.Build().Run();
