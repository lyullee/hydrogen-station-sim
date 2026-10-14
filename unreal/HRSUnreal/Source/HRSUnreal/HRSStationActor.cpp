#include "HRSStationActor.h"
#include "HttpModule.h"
#include "Interfaces/IHttpResponse.h"
#include "WebSocketsModule.h"
#include "IWebSocket.h"
#include "Async/Async.h"
#include "Components/StaticMeshComponent.h"
#include "Components/TextRenderComponent.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonReader.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "TimerManager.h"
#include "Camera/PlayerCameraManager.h"
#include "GameFramework/PlayerController.h"
#include "Engine/World.h"
#include "Materials/MaterialInterface.h"
#include "Misc/DateTime.h"

namespace
{
    const TCHAR* Cube = TEXT("/Engine/BasicShapes/Cube.Cube");
    const TCHAR* Cylinder = TEXT("/Engine/BasicShapes/Cylinder.Cylinder");
    const TCHAR* Sphere = TEXT("/Engine/BasicShapes/Sphere.Sphere");
    FString Str(const TSharedPtr<FJsonObject>& Object, const TCHAR* Key)
    { FString Value; if (Object) Object->TryGetStringField(Key, Value); return Value; }
    double Num(const TSharedPtr<FJsonObject>& Object, const TCHAR* Key, double Default = 0)
    { double Value; return Object && Object->TryGetNumberField(Key, Value) ? Value : Default; }
    bool Bool(const TSharedPtr<FJsonObject>& Object, const TCHAR* Key, bool Default = false)
    { bool Value; return Object && Object->TryGetBoolField(Key, Value) ? Value : Default; }
    TSharedPtr<FJsonObject> Obj(const TSharedPtr<FJsonObject>& Object, const TCHAR* Key)
    { const TSharedPtr<FJsonObject>* Value; return Object && Object->TryGetObjectField(Key, Value) ? *Value : nullptr; }
    TSharedPtr<FJsonObject> Parse(const FString& Value)
    { TSharedPtr<FJsonObject> Result; FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Value), Result); return Result; }
    FString DisplayNumber(const TSharedPtr<FJsonObject>& Object, const TCHAR* Key)
    { double Value; return Object && Object->TryGetNumberField(Key, Value) ? FString::Printf(TEXT("%.2f"), Value) : TEXT("--"); }
}

AHRSStationActor::AHRSStationActor()
{
    PrimaryActorTick.bCanEverTick = true;
    SceneRoot = CreateDefaultSubobject<USceneComponent>(TEXT("Station"));
    RootComponent = SceneRoot;
}

UStaticMeshComponent* AHRSStationActor::Shape(const TCHAR* MeshPath, const FVector& Position,
    const FVector& Size, const FLinearColor& Color, bool bTransparent, const FString& ComponentId)
{
    auto* Mesh = NewObject<UStaticMeshComponent>(this);
    Mesh->SetupAttachment(SceneRoot);
    Mesh->SetStaticMesh(LoadObject<UStaticMesh>(nullptr, MeshPath));
    Mesh->SetRelativeLocation(Position);
    Mesh->SetRelativeScale3D(Size / 100.f);
    Mesh->SetMobility(EComponentMobility::Movable);
    Mesh->SetCollisionEnabled(bTransparent ? ECollisionEnabled::NoCollision : ECollisionEnabled::QueryOnly);
    Mesh->SetCollisionResponseToAllChannels(ECR_Ignore);
    if (!bTransparent) Mesh->SetCollisionResponseToChannel(ECC_Visibility, ECR_Block);
    if (!ComponentId.IsEmpty()) Mesh->ComponentTags.Add(FName(*ComponentId));
    UMaterialInterface* Base = bTransparent ? TransparentMaterial.Get() : OpaqueMaterial.Get();
    if (Base)
    {
        auto* Dynamic = UMaterialInstanceDynamic::Create(Base, this);
        Dynamic->SetVectorParameterValue(TEXT("Color"), Color);
        Mesh->SetMaterial(0, Dynamic);
    }
    AddInstanceComponent(Mesh); Mesh->RegisterComponent();
    return Mesh;
}

UTextRenderComponent* AHRSStationActor::Text(const FVector& Position, const FString& Value, float Size)
{
    auto* Label = NewObject<UTextRenderComponent>(this);
    Label->SetupAttachment(SceneRoot); Label->SetRelativeLocation(Position);
    Label->SetWorldSize(Size); Label->SetText(FText::FromString(Value));
    Label->SetTextRenderColor(FColor(25, 48, 68)); Label->SetHorizontalAlignment(EHTA_Center);
    AddInstanceComponent(Label); Label->RegisterComponent(); return Label;
}

void AHRSStationActor::Tint(UStaticMeshComponent* Mesh, const FLinearColor& Color)
{
    if (auto* Material = Cast<UMaterialInstanceDynamic>(Mesh->GetMaterial(0)))
        Material->SetVectorParameterValue(TEXT("Color"), Color);
}

void AHRSStationActor::BuildBank(const FString& Bank, const FVector& Origin, const FLinearColor& Color)
{
    const FString Id = TEXT("cascade.") + Bank;
    Origins.Add(Id, Origin); Dimensions.Add(Id, FVector(265, 460, 280));
    Names.Add(Id, Bank.ToUpper());
    Shape(Cube, Origin + FVector(0, 0, 12), FVector(265, 460, 24), FLinearColor(.65, .69, .7), false, Id);
    for (double X : {-84., 84.}) for (double Y : {-155., 155.})
        Shape(Cube, Origin + FVector(X, Y, 143.5), FVector(13, 13, 239), Color, false, Id);
    for (double Y : {-155., 155.})
        Shape(Cube, Origin + FVector(0, Y, 261), FVector(182, 11, 10), Color, false, Id);
    for (double Z : {66., 136., 206.}) for (double X : {-45., 45.})
    {
        auto* Vessel = Shape(Cylinder, Origin + FVector(X, 0, Z), FVector(41, 41, 249),
                             FLinearColor(.72, .75, .76), false, Id);
        Vessel->SetRelativeRotation(FRotator(90, 0, 0));
        for (double Y : {-124.5, 124.5})
            Shape(Sphere, Origin + FVector(X, Y, Z), FVector(41), FLinearColor(.72, .75, .76), false, Id);
    }
    for (bool bInlet : {true, false})
    {
        const FString ValveId = TEXT("bank.") + Bank + (bInlet ? TEXT(".inlet") : TEXT(".outlet"));
        auto* Valve = Shape(Cylinder, Origin + FVector(0, bInlet ? -215 : 215, 60), FVector(28, 28, 22),
                            FLinearColor(.1, .55, .35), false, Id);
        ValveMeshes.Add(ValveId, Valve);
    }
    Labels.Add(Id, Text(Origin + FVector(0, 0, 330), Bank.ToUpper() + TEXT("\nP -- MPa  T -- C\nInventory -- kg")));
    RiskMeshes.Add(Id, Shape(Cube, Origin + FVector(0, 0, 25), FVector(305, 500, 2), Color, true));
    RiskMeshes[Id]->SetVisibility(false);
}

void AHRSStationActor::BeginPlay()
{
    Super::BeginPlay();
    FParse::Value(FCommandLine::Get(), TEXT("HRSApi="), ApiBase);
    FParse::Value(FCommandLine::Get(), TEXT("HRSRenderer="), RendererId);
    ApiBase.RemoveFromEnd(TEXT("/"));
    OpaqueMaterial = LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/HRS/Materials/M_HRSOpaque.M_HRSOpaque"));
    TransparentMaterial = LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/HRS/Materials/M_HRSTranslucent.M_HRSTranslucent"));
    Shape(Cube, FVector(300, -600, -15), FVector(2300, 1300, 30), FLinearColor(.72, .77, .8));
    BuildBank(TEXT("low"), FVector(-100, -600, 0), FLinearColor(.1, .48, .53));
    BuildBank(TEXT("medium"), FVector(300, -600, 0), FLinearColor(.52, .34, .13));
    BuildBank(TEXT("high"), FVector(700, -600, 0), FLinearColor(.32, .23, .56));
    StatusText = Text(FVector(300, -900, 450), TEXT("Waiting for station session\n1/2/3 select | X inlet close | Z outlet close\nE ESD | F stop | R risk | D distance"), 22);
    GetWorldTimerManager().SetTimer(SessionTimer, this, &AHRSStationActor::PollBinding, 1.f, true, 0.f);
}

void AHRSStationActor::ResetVisualState()
{
    LastSequence = -1; LastSnapshotTicks = 0; LastReceive = 0; bTerminal = false;
    bShowRisk = false; bShowDistance = false; Selected = TEXT("cascade.high");
    for (auto& Row : Jets) { RemoveInstanceComponent(Row.Value); Row.Value->DestroyComponent(); }
    for (auto& Row : DistanceMeshes) { RemoveInstanceComponent(Row.Value); Row.Value->DestroyComponent(); }
    Jets.Empty(); DistanceMeshes.Empty();
    for (auto& Row : RiskMeshes) Row.Value->SetVisibility(false);
    for (auto& Row : ValveMeshes) Tint(Row.Value, FLinearColor(.45, .45, .45));
    for (auto& Row : Labels) Row.Value->SetText(FText::FromString(Names[Row.Key] + TEXT("\nP -- MPa  T -- C\nInventory -- kg")));
    StatusText->SetText(FText::FromString(TEXT("No active renderer session")));
}

void AHRSStationActor::PollBinding()
{
    if (bBindingPending) return;
    bBindingPending = true;
    PendingBinding = FHttpModule::Get().CreateRequest();
    PendingBinding->SetURL(ApiBase + TEXT("/api/integrations/unreal/session/") + RendererId);
    PendingBinding->SetVerb(TEXT("GET")); PendingBinding->SetTimeout(4.f);
    TWeakObjectPtr<AHRSStationActor> Weak(this);
    PendingBinding->OnProcessRequestComplete().BindLambda([Weak](FHttpRequestPtr, FHttpResponsePtr Response, bool bSuccess)
    {
        if (!Weak.IsValid()) return;
        auto* Self = Weak.Get(); Self->bBindingPending = false;
        auto Data = bSuccess && Response.IsValid() && Response->GetResponseCode() == 200 ? Parse(Response->GetContentAsString()) : nullptr;
        if (!Data) return;
        const FString Run = Str(Data, TEXT("run_id"));
        const int32 NewGeneration = (int32)Num(Data, TEXT("generation"));
        if (Run != Self->CurrentRun || NewGeneration != Self->Generation)
        {
            Self->Generation = NewGeneration; Self->CurrentRun = Run;
            if (Self->Socket) Self->Socket->Close();
            Self->Socket.Reset(); Self->bConnecting = false; Self->NextRetry = 0; Self->RetryDelay = 1;
            Self->ResetVisualState();
        }
        if (!Run.IsEmpty() && !Self->bTerminal && (!Self->Socket || !Self->Socket->IsConnected()))
        {
            if (!Self->bConnecting && FPlatformTime::Seconds() >= Self->NextRetry) Self->ConnectStream();
            Self->RequestSnapshot(); // HTTP fallback during WebSocket outages.
        }
        if (!Run.IsEmpty() && Self->bShowRisk && FPlatformTime::Seconds() - Self->LastRiskRequest >= 30)
            Self->RequestRisk();
    });
    if (!PendingBinding->ProcessRequest()) bBindingPending = false;
}

void AHRSStationActor::ConnectStream()
{
    FString Url = ApiBase; Url.ReplaceInline(TEXT("https://"), TEXT("wss://"));
    Url.ReplaceInline(TEXT("http://"), TEXT("ws://"));
    Url += TEXT("/api/simulations/") + CurrentRun + TEXT("/visualization/stream");
    const int32 Expected = Generation;
    const int32 ExpectedConnection = ++ConnectionSerial;
    bConnecting = true; NextRetry = FPlatformTime::Seconds() + RetryDelay;
    RetryDelay = FMath::Min(10., RetryDelay * 2.);
    Socket = FWebSocketsModule::Get().CreateWebSocket(Url);
    TWeakObjectPtr<AHRSStationActor> Weak(this);
    Socket->OnConnected().AddLambda([Weak, Expected]() {
        if (Weak.IsValid() && Weak->Generation == Expected) { Weak->bConnecting = false; Weak->RetryDelay = 1; }
    });
    Socket->OnConnectionError().AddLambda([Weak, Expected](const FString&) {
        if (Weak.IsValid() && Weak->Generation == Expected) Weak->bConnecting = false;
    });
    Socket->OnClosed().AddLambda([Weak, Expected](int32, const FString&, bool) {
        if (Weak.IsValid() && Weak->Generation == Expected) Weak->bConnecting = false;
    });
    Socket->OnMessage().AddLambda([Weak, Expected, ExpectedConnection](const FString& Message) {
        AsyncTask(ENamedThreads::GameThread, [Weak, Expected, ExpectedConnection, Message]() {
            if (!Weak.IsValid() || Weak->Generation != Expected || Weak->ConnectionSerial != ExpectedConnection) return;
            const auto Packet = Parse(Message);
            if (Str(Packet, TEXT("type")) == TEXT("snapshot")) Weak->ApplySnapshot(Obj(Packet, TEXT("snapshot")));
        });
    });
    Socket->Connect();
}

void AHRSStationActor::RequestSnapshot()
{
    if (bSnapshotPending) return;
    bSnapshotPending = true; const int32 Expected = Generation;
    PendingSnapshot = FHttpModule::Get().CreateRequest();
    PendingSnapshot->SetURL(ApiBase + TEXT("/api/simulations/") + CurrentRun + TEXT("/visualization/snapshot"));
    PendingSnapshot->SetVerb(TEXT("GET")); PendingSnapshot->SetTimeout(4.f);
    TWeakObjectPtr<AHRSStationActor> Weak(this);
    PendingSnapshot->OnProcessRequestComplete().BindLambda([Weak, Expected](FHttpRequestPtr, FHttpResponsePtr Response, bool bSuccess) {
        if (!Weak.IsValid()) return;
        Weak->bSnapshotPending = false;
        if (Weak->Generation == Expected && bSuccess && Response.IsValid() && Response->GetResponseCode() == 200)
            Weak->ApplySnapshot(Parse(Response->GetContentAsString()));
    });
    if (!PendingSnapshot->ProcessRequest()) bSnapshotPending = false;
}

void AHRSStationActor::ApplySnapshot(const TSharedPtr<FJsonObject>& Snapshot)
{
    if (!Snapshot || Num(Snapshot, TEXT("schema_version")) != 1 || Str(Snapshot, TEXT("run_id")) != CurrentRun) return;
    FDateTime Produced;
    if (FDateTime::ParseIso8601(*Str(Snapshot, TEXT("produced_at")), Produced))
    {
        if (Produced.GetTicks() < LastSnapshotTicks) return;
        LastSnapshotTicks = Produced.GetTicks();
    }
    const int64 Sequence = (int64)Num(Snapshot, TEXT("sequence"), -1);
    if (Sequence < LastSequence) return;
    LastSequence = Sequence; LastReceive = FPlatformTime::Seconds();
    const FString Status = Str(Snapshot, TEXT("status"));
    bTerminal = Status == TEXT("complete") || Status == TEXT("failed") || Status == TEXT("stopped") || Status == TEXT("cancelled");
    bool bEsdValue = false;
    const bool bHasEsd = Snapshot->TryGetBoolField(TEXT("esd"), bEsdValue);
    StatusText->SetText(FText::FromString(FString::Printf(TEXT("Simulation %.1f s | %s | %s\n1/2/3 select | X inlet | Z outlet | E ESD | F stop | R risk | D distance"),
        Num(Snapshot, TEXT("time_s")), *Status, !bHasEsd ? TEXT("ESD unknown") : bEsdValue ? TEXT("ESD active") : TEXT("ESD standby"))));
    const TArray<TSharedPtr<FJsonValue>>* Rows;
    if (Snapshot->TryGetArrayField(TEXT("equipment"), Rows)) for (const auto& Item : *Rows)
    {
        const auto Row = Item->AsObject(); if (!Row) continue;
        const FString Id = Str(Row, TEXT("component_id")); if (!Labels.Contains(Id)) continue;
        Labels[Id]->SetText(FText::FromString(Names[Id] + TEXT("\nP ") + DisplayNumber(Row, TEXT("pressure_mpa")) +
            TEXT(" MPa  T ") + DisplayNumber(Row, TEXT("temperature_c")) + TEXT(" C\nInventory ") + DisplayNumber(Row, TEXT("mass_kg")) + TEXT(" kg")));
    }
    const auto Valves = Obj(Obj(Snapshot, TEXT("safety")), TEXT("valves"));
    for (auto& Mesh : ValveMeshes)
    {
        const auto Valve = Obj(Valves, *Mesh.Key);
        FLinearColor Color(.45, .45, .45);
        if (Valve) Color = Str(Valve, TEXT("status")) == TEXT("failed") ? FLinearColor(.7, .05, .08) :
            Str(Valve, TEXT("status")) == TEXT("moving") || Str(Valve, TEXT("status")) == TEXT("commanded") ? FLinearColor(.8, .4, .04) :
            Bool(Valve, TEXT("actual_open")) ? FLinearColor(.1, .55, .35) : FLinearColor(.16, .23, .32);
        Tint(Mesh.Value, Color);
        if (Valve) Mesh.Value->SetRelativeRotation(FRotator(0, Bool(Valve, TEXT("actual_open")) ? 0 : 90, 0));
    }
    for (auto& Row : Jets) Row.Value->SetVisibility(false);
    for (auto& Row : DistanceMeshes) Row.Value->SetVisibility(false);
    if (Snapshot->TryGetArrayField(TEXT("releases"), Rows)) for (const auto& Item : *Rows)
    {
        const auto Row = Item->AsObject(); if (!Row) continue;
        const FString Id = Str(Row, TEXT("component_id")), Release = Str(Row, TEXT("release_id"));
        const double Flow = Num(Row, TEXT("mass_flow_g_s"));
        if (!Origins.Contains(Id) || Flow <= 1.e-6 || Release.IsEmpty()) continue;
        const FVector Origin = Origins[Id] + FVector(0, 0, Num(Row, TEXT("outlet_height_m"), 1.5) * 100);
        const double Height = FMath::Clamp(60. + FMath::Sqrt(Flow) * 15., 60., 450.); // Schematic, not CFD.
        if (!Jets.Contains(Release)) Jets.Add(Release, Shape(Cylinder, Origin, FVector(25, 25, Height), FLinearColor(.12, .5, .65), true));
        Jets[Release]->SetRelativeLocation(Origin + FVector(0, 0, Height / 2));
        Jets[Release]->SetRelativeScale3D(FVector(.25, .25, Height / 100)); Jets[Release]->SetVisibility(true);
        const double Radius = FMath::Max(Num(Row, TEXT("sampled_effect_radius_m")), Num(Row, TEXT("flammable_plume_distance_m"))) * 100;
        if (Radius > 0)
        {
            if (!DistanceMeshes.Contains(Release)) DistanceMeshes.Add(Release,
                Shape(Cylinder, Origins[Id] + FVector(0, 0, 28), FVector(Radius * 2, Radius * 2, 3), FLinearColor(.85, .22, .08), true));
            DistanceMeshes[Release]->SetRelativeScale3D(FVector(Radius / 50, Radius / 50, .03));
            DistanceMeshes[Release]->SetVisibility(bShowDistance);
        }
    }
    ApplyRisk(Obj(Snapshot, TEXT("risk_zones")));
}

void AHRSStationActor::ApplyRisk(const TSharedPtr<FJsonObject>& Risk)
{
    for (auto& Row : RiskMeshes) Row.Value->SetVisibility(false);
    const TArray<TSharedPtr<FJsonValue>>* Rows;
    if (!Risk || !Risk->TryGetArrayField(TEXT("zones"), Rows)) return;
    for (const auto& Item : *Rows)
    {
        const auto Row = Item->AsObject(); if (!Row) continue;
        const FString Id = Str(Row, TEXT("component")); if (!RiskMeshes.Contains(Id)) continue;
        const double Score = Num(Row, TEXT("absolute_score"));
        Tint(RiskMeshes[Id], Score >= 60 ? FLinearColor(.85, .18, .08) : Score >= 35 ? FLinearColor(.8, .5, .08) : FLinearColor(.08, .48, .35));
        RiskMeshes[Id]->SetVisibility(bShowRisk);
    }
}

void AHRSStationActor::RequestRisk()
{
    LastRiskRequest = FPlatformTime::Seconds(); const int32 Expected = Generation;
    auto Request = FHttpModule::Get().CreateRequest();
    Request->SetURL(ApiBase + TEXT("/api/simulations/") + CurrentRun + TEXT("/risk-zones"));
    Request->SetVerb(TEXT("GET")); Request->SetTimeout(15.f);
    TWeakObjectPtr<AHRSStationActor> Weak(this);
    Request->OnProcessRequestComplete().BindLambda([Weak, Expected](FHttpRequestPtr, FHttpResponsePtr Response, bool bSuccess) {
        if (Weak.IsValid() && Weak->Generation == Expected && bSuccess && Response.IsValid() && Response->GetResponseCode() == 200)
            Weak->ApplyRisk(Parse(Response->GetContentAsString()));
    });
    Request->ProcessRequest();
}

void AHRSStationActor::IssueAction(const FString& Kind, const FString& Target)
{
    if (CurrentRun.IsEmpty() || bTerminal) return;
    auto Request = FHttpModule::Get().CreateRequest();
    Request->SetURL(ApiBase + TEXT("/api/simulations/") + CurrentRun + TEXT("/safety/actions"));
    Request->SetVerb(TEXT("POST")); Request->SetHeader(TEXT("Content-Type"), TEXT("application/json"));
    Request->SetTimeout(5.f);
    auto Data = MakeShared<FJsonObject>(); Data->SetStringField(TEXT("kind"), Kind);
    Data->SetStringField(TEXT("target"), Target); Data->SetStringField(TEXT("note"), TEXT("Unreal virtual operator"));
    FString Body; FJsonSerializer::Serialize(Data, TJsonWriterFactory<>::Create(&Body));
    Request->SetContentAsString(Body);
    TWeakObjectPtr<AHRSStationActor> Weak(this); const int32 Expected = Generation;
    Request->OnProcessRequestComplete().BindLambda([Weak, Expected](FHttpRequestPtr, FHttpResponsePtr Response, bool bSuccess) {
        if (!Weak.IsValid() || Weak->Generation != Expected) return;
        const FString Message = !bSuccess || !Response.IsValid() ? TEXT("Command transport failed; inspect before retry") :
            Response->GetResponseCode() == 200 ? TEXT("Command accepted; waiting for actuator feedback") : TEXT("Command rejected; inspect safety prerequisites");
        Weak->StatusText->SetText(FText::FromString(Message));
        Weak->RequestSnapshot(); // No optimistic closure and no automatic command retry.
    });
    Request->ProcessRequest();
}

void AHRSStationActor::Select(const FString& Id) { if (Origins.Contains(Id)) Selected = Id; }
void AHRSStationActor::CloseSelectedValve(bool bInlet)
{ FString Bank = Selected; Bank.RemoveFromStart(TEXT("cascade.")); IssueAction(TEXT("valve.close"), TEXT("bank.") + Bank + (bInlet ? TEXT(".inlet") : TEXT(".outlet"))); }
void AHRSStationActor::ToggleRisk() { bShowRisk = !bShowRisk; if (!CurrentRun.IsEmpty()) RequestRisk(); }
void AHRSStationActor::ToggleDistance() { bShowDistance = !bShowDistance; RequestSnapshot(); }

void AHRSStationActor::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    const auto* Controller = GetWorld()->GetFirstPlayerController();
    if (Controller && Controller->PlayerCameraManager)
    {
        const FVector Camera = Controller->PlayerCameraManager->GetCameraLocation();
        StatusText->SetWorldRotation((Camera - StatusText->GetComponentLocation()).Rotation());
        for (auto& Row : Labels) Row.Value->SetWorldRotation((Camera - Row.Value->GetComponentLocation()).Rotation());
    }
    if (!bTerminal && !CurrentRun.IsEmpty() && LastReceive > 0 && FPlatformTime::Seconds() - LastReceive > 3)
        StatusText->SetText(FText::FromString(TEXT("DATA STALE - waiting for connection; last values retained")));
}

void AHRSStationActor::EndPlay(const EEndPlayReason::Type Reason)
{
    GetWorldTimerManager().ClearTimer(SessionTimer);
    if (Socket) Socket->Close();
    if (PendingBinding) PendingBinding->CancelRequest();
    if (PendingSnapshot) PendingSnapshot->CancelRequest();
    Super::EndPlay(Reason);
}
