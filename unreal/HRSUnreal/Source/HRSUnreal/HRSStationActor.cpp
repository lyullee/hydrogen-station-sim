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
#include "EngineUtils.h"
#include "Materials/MaterialInterface.h"
#include "Misc/DateTime.h"
#include "Math/RotationMatrix.h"

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
    if (!Mesh) return;
    if (auto* Material = Cast<UMaterialInstanceDynamic>(Mesh->GetMaterial(0)))
        Material->SetVectorParameterValue(TEXT("Color"), Color);
}

UStaticMeshComponent* AHRSStationActor::Segment(const FVector& Start, const FVector& End,
    float Diameter, const FLinearColor& Color, bool bTransparent, const FString& ComponentId)
{
    const FVector Direction = End - Start;
    auto* Part = Shape(Cylinder, (Start + End) * .5f,
                       FVector(Diameter, Diameter, FMath::Max(Direction.Size(), 1.0)),
                       Color, bTransparent, ComponentId);
    Part->SetRelativeRotation(FRotationMatrix::MakeFromZ(Direction.GetSafeNormal()).Rotator());
    return Part;
}

void AHRSStationActor::BuildHose(TArray<TObjectPtr<UStaticMeshComponent>>& Parts,
    const TArray<FVector>& Points, const FString& ComponentId)
{
    for (int32 Index = 1; Index < Points.Num(); ++Index)
        Parts.Add(Segment(Points[Index - 1], Points[Index], 8.f,
                          FLinearColor(.04, .055, .065), false, ComponentId));
}

void AHRSStationActor::BuildBank(const FString& Bank, const FVector& Origin, const FLinearColor& Color)
{
    const FString Id = TEXT("cascade.") + Bank;
    Origins.Add(Id, Origin); Dimensions.Add(Id, FVector(265, 460, 280));
    Names.Add(Id, Bank.ToUpper());
    auto* Base = Shape(Cube, Origin + FVector(0, 0, 12), FVector(265, 460, 24), FLinearColor(.65, .69, .7), false, Id);
    EquipmentMeshes.Add(Id, Base);
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
    HighlightMeshes.Add(Id, Shape(Cube, Origin + FVector(0, 0, 155), FVector(290, 490, 310),
                                  FLinearColor(.8, .08, .04), true));
    HighlightMeshes[Id]->SetVisibility(false);
    FireMeshes.Add(Id, Shape(Cylinder, Origin + FVector(0, 0, 345), FVector(65, 65, 220),
                             FLinearColor(.95, .18, .025), true));
    FireMeshes[Id]->SetVisibility(false);
    AuxiliaryMeshes.Add(TEXT("purge.") + Bank,
        Shape(Cylinder, Origin + FVector(0, 0, 360), FVector(35, 35, 220),
              FLinearColor(.18, .55, .82), true));
    AuxiliaryMeshes[TEXT("purge.") + Bank]->SetVisibility(false);
    AuxiliaryMeshes.Add(TEXT("diagnostic.") + Bank,
        Shape(Sphere, Origin + FVector(0, 0, 315), FVector(52),
              FLinearColor(.84, .56, .08), true));
    AuxiliaryMeshes[TEXT("diagnostic.") + Bank]->SetVisibility(false);
}

void AHRSStationActor::BuildReferenceStation()
{
    // Public-reference layout. Geometry is intentionally generic and does not
    // disclose the footprint, manufacturer, or capacity of a real station.
    Shape(Cube, FVector(-400, -100, -20), FVector(4800, 2800, 40),
          FLinearColor(.67, .72, .74));
    Shape(Cube, FVector(-350, 900, 2), FVector(4700, 520, 8),
          FLinearColor(.13, .16, .18));
    for (int32 X = -2500; X <= 1700; X += 500)
        Shape(Cube, FVector(X, 900, 8), FVector(220, 9, 3), FLinearColor(.9, .9, .82));

    auto AddEquipment = [this](const FString& Id, const FString& Label,
        const FVector& Origin, const FVector& Envelope, const FLinearColor& Color)
    {
        Origins.Add(Id, Origin); Dimensions.Add(Id, Envelope); Names.Add(Id, Label);
        auto* Body = Shape(Cube, Origin + FVector(0, 0, Envelope.Z * .5f), Envelope,
                           Color, false, Id);
        EquipmentMeshes.Add(Id, Body);
        Labels.Add(Id, Text(Origin + FVector(0, 0, Envelope.Z + 55),
                            Label + TEXT("\nP -- MPa  T -- C\nFlow -- g/s"), 19));
        RiskMeshes.Add(Id, Shape(Cube, Origin + FVector(0, 0, 5),
                                 FVector(Envelope.X + 70, Envelope.Y + 70, 3), Color, true));
        HighlightMeshes.Add(Id, Shape(Cube, Origin + FVector(0, 0, Envelope.Z * .5f),
                                      Envelope + FVector(35, 35, 35),
                                      FLinearColor(.78, .055, .025), true));
        FireMeshes.Add(Id, Shape(Cylinder, Origin + FVector(0, 0, Envelope.Z + 100),
                                 FVector(55, 55, 200), FLinearColor(.95, .17, .02), true));
        RiskMeshes[Id]->SetVisibility(false); HighlightMeshes[Id]->SetVisibility(false);
        FireMeshes[Id]->SetVisibility(false);
    };

    AddEquipment(TEXT("supply"), TEXT("SUPPLY TRAILER"), FVector(-2200, -150, 0),
                 FVector(260, 1600, 370), FLinearColor(.72, .76, .77));
    for (float X : {-2270.f, -2200.f, -2130.f})
        Segment(FVector(X, -720, 125), FVector(X, 420, 125), 46,
                FLinearColor(.88, .9, .91), false, TEXT("supply"));
    Shape(Cube, FVector(-2200, 560, 120), FVector(235, 230, 240),
          FLinearColor(.08, .36, .29), false, TEXT("supply"));

    AddEquipment(TEXT("compressor"), TEXT("COMPRESSOR"), FVector(-640, -600, 0),
                 FVector(500, 440, 360), FLinearColor(.17, .38, .39));
    AddEquipment(TEXT("cooler"), TEXT("PRE-COOLER"), FVector(1100, -600, 0),
                 FVector(420, 400, 300), FLinearColor(.15, .34, .37));
    AddEquipment(TEXT("header"), TEXT("COMMON HEADER"), FVector(300, -300, 0),
                 FVector(400, 100, 150), FLinearColor(.55, .59, .61));
    AddEquipment(TEXT("dispenser.pcv"), TEXT("DISPENSER 1"), FVector(0, 420, 0),
                 FVector(120, 100, 220), FLinearColor(.94, .95, .96));
    AddEquipment(TEXT("dispenser_2.pcv"), TEXT("DISPENSER 2"), FVector(800, 420, 0),
                 FVector(120, 100, 220), FLinearColor(.94, .95, .96));
    AddEquipment(TEXT("vehicle.tank"), TEXT("VEHICLE 1"), FVector(280, 700, 0),
                 FVector(490, 190, 150), FLinearColor(.33, .38, .4));
    AddEquipment(TEXT("vehicle_2.tank"), TEXT("VEHICLE 2"), FVector(1080, 700, 0),
                 FVector(490, 190, 150), FLinearColor(.33, .38, .4));
    AddEquipment(TEXT("vent"), TEXT("VENT STACK"), FVector(1400, -900, 0),
                 FVector(100, 100, 600), FLinearColor(.58, .64, .65));
    AddEquipment(TEXT("dispenser.hose"), TEXT("HOSE 1"), FVector(180, 520, 0),
                 FVector(240, 200, 100), FLinearColor(.08, .1, .11));
    AddEquipment(TEXT("dispenser_2.hose"), TEXT("HOSE 2"), FVector(980, 520, 0),
                 FVector(240, 200, 100), FLinearColor(.08, .1, .11));
    EquipmentMeshes[TEXT("dispenser.hose")]->SetVisibility(false);
    EquipmentMeshes[TEXT("dispenser_2.hose")]->SetVisibility(false);

    auto AddValve = [this](const FString& ValveId, const FString& ComponentId, const FVector& Position)
    {
        ValveMeshes.Add(ValveId, Shape(Cylinder, Position, FVector(28, 28, 22),
                                       FLinearColor(.1, .55, .35), false, ComponentId));
    };
    AddValve(TEXT("trailer.source"), TEXT("supply"), FVector(-2200, 400, 70));
    AddValve(TEXT("trailer.station"), TEXT("supply"), FVector(-900, -550, 70));
    AddValve(TEXT("compressor.suction"), TEXT("compressor"), FVector(-880, -600, 80));
    AddValve(TEXT("compressor.discharge"), TEXT("compressor"), FVector(-400, -600, 80));
    AddValve(TEXT("dispenser.1"), TEXT("dispenser.pcv"), FVector(0, 360, 80));
    AddValve(TEXT("dispenser.2"), TEXT("dispenser_2.pcv"), FVector(800, 360, 80));
    AddValve(TEXT("vent.low"), TEXT("vent"), FVector(1340, -900, 90));
    AddValve(TEXT("vent.medium"), TEXT("vent"), FVector(1400, -900, 90));
    AddValve(TEXT("vent.high"), TEXT("vent"), FVector(1460, -900, 90));

    // Canopy, operations room, perimeter and pipe corridor establish scale.
    Shape(Cube, FVector(420, 565, 500), FVector(1900, 900, 35), FLinearColor(.9, .92, .93));
    for (float X : {-450.f, 420.f, 1290.f}) for (float Y : {180.f, 950.f})
        Shape(Cube, FVector(X, Y, 245), FVector(28, 28, 490), FLinearColor(.72, .76, .78));
    Shape(Cube, FVector(-1000, 500, 150), FVector(560, 520, 300), FLinearColor(.87, .89, .89));
    for (float Y : {-1120.f, 1120.f})
        Shape(Cube, FVector(-400, Y, 105), FVector(4800, 15, 210), FLinearColor(.22, .31, .33));
    Segment(FVector(-2200, -550, 70), FVector(-900, -550, 70), 15, FLinearColor(.79, .62, .12));
    Segment(FVector(-900, -550, 70), FVector(-900, -300, 70), 15, FLinearColor(.79, .62, .12));
    Segment(FVector(-900, -300, 70), FVector(1350, -300, 70), 15, FLinearColor(.08, .55, .46));

    BuildHose(Hose1Parked, {FVector(50, 430, 175), FVector(95, 455, 130),
        FVector(90, 510, 45), FVector(35, 520, 80), FVector(45, 470, 165)}, TEXT("dispenser.hose"));
    BuildHose(Hose2Parked, {FVector(850, 430, 175), FVector(895, 455, 130),
        FVector(890, 510, 45), FVector(835, 520, 80), FVector(845, 470, 165)}, TEXT("dispenser_2.hose"));
    BuildHose(Hose1Connected, {FVector(50, 430, 175), FVector(115, 500, 100),
        FVector(180, 620, 55), FVector(250, 650, 80)}, TEXT("dispenser.hose"));
    BuildHose(Hose2Connected, {FVector(850, 430, 175), FVector(915, 500, 100),
        FVector(980, 620, 55), FVector(1050, 650, 80)}, TEXT("dispenser_2.hose"));
    for (auto Part : Hose1Connected) Part->SetVisibility(false);
    for (auto Part : Hose2Connected) Part->SetVisibility(false);

    const TArray<TPair<FString, FVector>> Detectors = {
        TPair<FString, FVector>(TEXT("GD-0101"), FVector(-2200, 500, 270)), TPair<FString, FVector>(TEXT("GD-0201"), FVector(-2200, -800, 250)),
        TPair<FString, FVector>(TEXT("GD-0601"), FVector(-600, -400, 280)), TPair<FString, FVector>(TEXT("GD-0701"), FVector(-200, -500, 270)),
        TPair<FString, FVector>(TEXT("GD-0801"), FVector(100, -500, 270)), TPair<FString, FVector>(TEXT("GD-0901"), FVector(500, -500, 270)),
        TPair<FString, FVector>(TEXT("GD-1001"), FVector(800, -300, 270)), TPair<FString, FVector>(TEXT("GD-1301"), FVector(0, 425, 466)),
        TPair<FString, FVector>(TEXT("GD-1701"), FVector(800, 425, 466)), TPair<FString, FVector>(TEXT("GD-1901"), FVector(1100, -400, 270)),
        TPair<FString, FVector>(TEXT("GD-2001"), FVector(1200, -300, 280)), TPair<FString, FVector>(TEXT("GD-2101"), FVector(-600, -300, 380)),
        TPair<FString, FVector>(TEXT("GD-2201"), FVector(300, -500, 370)), TPair<FString, FVector>(TEXT("GD-2301"), FVector(400, 400, 470)),
        TPair<FString, FVector>(TEXT("GD-2302"), FVector(1100, -400, 350)), TPair<FString, FVector>(TEXT("FD-0101"), FVector(-2200, 300, 330)),
        TPair<FString, FVector>(TEXT("FD-0601"), FVector(-600, -300, 370)), TPair<FString, FVector>(TEXT("FD-0701"), FVector(-200, -400, 350)),
        TPair<FString, FVector>(TEXT("FD-0801"), FVector(100, -400, 350)), TPair<FString, FVector>(TEXT("FD-0901"), FVector(500, -400, 350)),
        TPair<FString, FVector>(TEXT("FD-1301"), FVector(0, 360, 455)), TPair<FString, FVector>(TEXT("FD-1701"), FVector(800, 360, 455)),
        TPair<FString, FVector>(TEXT("FD-1901"), FVector(1100, -300, 360)), TPair<FString, FVector>(TEXT("FD-2001"), FVector(1200, -200, 350))
    };
    for (const auto& Entry : Detectors)
    {
        const bool bFlame = Entry.Key.StartsWith(TEXT("FD-"));
        auto* Marker = Shape(Sphere, Entry.Value, FVector(24),
                             bFlame ? FLinearColor(.94, .41, .08) : FLinearColor(.05, .55, .62),
                             false, Entry.Key);
        Marker->SetVisibility(false); DetectorMeshes.Add(Entry.Key, Marker);
    }
    const TArray<TPair<FString, FVector>> Cameras = {
        TPair<FString, FVector>(TEXT("CAM-01"), FVector(300, -360, 340)), TPair<FString, FVector>(TEXT("CAM-02"), FVector(-620, -380, 310)),
        TPair<FString, FVector>(TEXT("CAM-03"), FVector(410, 325, 360)), TPair<FString, FVector>(TEXT("CAM-04"), FVector(1350, -330, 300)),
        TPair<FString, FVector>(TEXT("CAM-05"), FVector(-2200, 120, 380))
    };
    for (const auto& Entry : Cameras)
    {
        auto* Camera = Shape(Cube, Entry.Value, FVector(34, 52, 28), FLinearColor(.12, .32, .44));
        Camera->SetVisibility(false); CameraMeshes.Add(Entry.Key, Camera);
    }

    for (const auto& Entry : TArray<TPair<FString, FVector>>{
        TPair<FString, FVector>(TEXT("unloading"), FVector(-1750, -150, 45)), TPair<FString, FVector>(TEXT("compressor"), FVector(-640, -120, 45)),
        TPair<FString, FVector>(TEXT("storage"), FVector(300, -80, 45)), TPair<FString, FVector>(TEXT("dispenser"), FVector(420, 1020, 45))})
        PersonnelMeshes.Add(Entry.Key, Shape(Sphere, Entry.Value, FVector(38), FLinearColor(.15, .35, .58)));
    for (const auto& Entry : TArray<TPair<FString, FVector>>{
        TPair<FString, FVector>(TEXT("fan.unloading"), FVector(-1750, -360, 260)), TPair<FString, FVector>(TEXT("fan.compressor"), FVector(-640, -340, 300)),
        TPair<FString, FVector>(TEXT("fan.storage"), FVector(300, -360, 300)), TPair<FString, FVector>(TEXT("fan.dispenser"), FVector(420, 160, 440)),
        TPair<FString, FVector>(TEXT("cooling.low"), FVector(-100, -360, 260)), TPair<FString, FVector>(TEXT("cooling.medium"), FVector(300, -360, 260)),
        TPair<FString, FVector>(TEXT("cooling.high"), FVector(700, -360, 260))})
        AuxiliaryMeshes.Add(Entry.Key, Shape(Cylinder, Entry.Value, FVector(38, 38, 20),
                                             FLinearColor(.35, .4, .42)));
    for (const auto& Entry : TArray<TPair<FString, FVector>>{
        TPair<FString, FVector>(TEXT("unloading"), FVector(-1750, -150, 6)), TPair<FString, FVector>(TEXT("compressor"), FVector(-640, -600, 6)),
        TPair<FString, FVector>(TEXT("storage"), FVector(300, -600, 6)), TPair<FString, FVector>(TEXT("dispenser"), FVector(420, 620, 6))})
    {
        auto* Boundary = Shape(Cube, Entry.Value, FVector(620, 620, 4),
                               FLinearColor(.82, .16, .05), true);
        Boundary->SetVisibility(false); AuxiliaryMeshes.Add(TEXT("access.") + Entry.Key, Boundary);
        auto* Power = Shape(Sphere, Entry.Value + FVector(0, 0, 80), FVector(28),
                            FLinearColor(.16, .55, .25));
        AuxiliaryMeshes.Add(TEXT("power.") + Entry.Key, Power);
    }
}

void AHRSStationActor::DiscoverImportedModels()
{
    ImportedModelActors.Empty();
    for (TActorIterator<AActor> It(GetWorld()); It; ++It)
    {
        AActor* Actor = *It;
        if (!Actor || Actor == this) continue;
        for (const FName& Tag : Actor->Tags)
        {
            const FString ComponentId = Tag.ToString();
            if (Origins.Contains(ComponentId))
            {
                ImportedModelActors.FindOrAdd(ComponentId).Add(Actor);
                break;
            }
        }
    }
    if (ImportedModelActors.Num() == 0) return;

    // Keep operational valves and overlays visible; hide only the tagged
    // primitive geometry that the imported reference scene replaces.
    TSet<UStaticMeshComponent*> ValveSet;
    for (const auto& Row : ValveMeshes) ValveSet.Add(Row.Value);
    TArray<UStaticMeshComponent*> Components;
    GetComponents<UStaticMeshComponent>(Components);
    for (UStaticMeshComponent* Component : Components)
    {
        if (!Component || ValveSet.Contains(Component)) continue;
        for (const FName& Tag : Component->ComponentTags)
        {
            if (ImportedModelActors.Contains(Tag.ToString()))
            {
                Component->SetVisibility(false);
                Component->SetCollisionEnabled(ECollisionEnabled::NoCollision);
                break;
            }
        }
    }
}

void AHRSStationActor::SetImportedModelVisibility(const FString& ComponentId, bool bVisible)
{
    const TArray<TWeakObjectPtr<AActor>>* Actors = ImportedModelActors.Find(ComponentId);
    if (!Actors) return;
    for (const TWeakObjectPtr<AActor>& WeakActor : *Actors)
    {
        if (AActor* Actor = WeakActor.Get())
        {
            Actor->SetActorHiddenInGame(!bVisible);
            Actor->SetActorEnableCollision(bVisible);
        }
    }
}

void AHRSStationActor::BeginPlay()
{
    Super::BeginPlay();
    FParse::Value(FCommandLine::Get(), TEXT("HRSApi="), ApiBase);
    FParse::Value(FCommandLine::Get(), TEXT("HRSRenderer="), RendererId);
    ApiBase.RemoveFromEnd(TEXT("/"));
    OpaqueMaterial = LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/HRS/Materials/M_HRSOpaque.M_HRSOpaque"));
    TransparentMaterial = LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/HRS/Materials/M_HRSTranslucent.M_HRSTranslucent"));
    BuildReferenceStation();
    BuildBank(TEXT("low"), FVector(-100, -600, 0), FLinearColor(.1, .48, .53));
    BuildBank(TEXT("medium"), FVector(300, -600, 0), FLinearColor(.52, .34, .13));
    BuildBank(TEXT("high"), FVector(700, -600, 0), FLinearColor(.32, .23, .56));
    DiscoverImportedModels();
    StatusText = Text(FVector(300, 1180, 520), TEXT("Waiting for station session\n1/2/3 select | X inlet | Z outlet | E ESD | F stop\nR risk | D distance | C cameras | G detectors"), 22);
    GetWorldTimerManager().SetTimer(SessionTimer, this, &AHRSStationActor::PollBinding, 1.f, true, 0.f);
}

void AHRSStationActor::ResetVisualState()
{
    if (PendingFeedback) PendingFeedback->CancelRequest();
    PendingFeedback.Reset(); bFeedbackPending = false;
    LastSequence = -1; LastFeedbackSequence = -1; LastSnapshotTicks = 0; LastReceive = 0; bTerminal = false;
    bShowRisk = false; bShowDistance = false; bShowCameras = false; bShowDetectors = false;
    Selected = TEXT("cascade.high");
    for (auto& Row : Jets) { RemoveInstanceComponent(Row.Value); Row.Value->DestroyComponent(); }
    for (auto& Row : DistanceMeshes) { RemoveInstanceComponent(Row.Value); Row.Value->DestroyComponent(); }
    Jets.Empty(); DistanceMeshes.Empty();
    for (auto& Row : RiskMeshes) Row.Value->SetVisibility(false);
    for (auto& Row : HighlightMeshes) Row.Value->SetVisibility(false);
    for (auto& Row : FireMeshes) Row.Value->SetVisibility(false);
    for (auto& Row : CameraMeshes) Row.Value->SetVisibility(false);
    for (auto& Row : DetectorMeshes) { Row.Value->SetVisibility(false); Tint(Row.Value,
        Row.Key.StartsWith(TEXT("FD-")) ? FLinearColor(.94, .41, .08) : FLinearColor(.05, .55, .62)); }
    for (auto& Row : AuxiliaryMeshes)
    {
        if (Row.Key.StartsWith(TEXT("access.")) || Row.Key.StartsWith(TEXT("purge.")) ||
            Row.Key.StartsWith(TEXT("diagnostic."))) Row.Value->SetVisibility(false);
        else if (Row.Key.StartsWith(TEXT("power."))) Tint(Row.Value, FLinearColor(.16, .55, .25));
        else Tint(Row.Value, FLinearColor(.35, .4, .42));
    }
    for (auto Part : Hose1Parked) Part->SetVisibility(true);
    for (auto Part : Hose2Parked) Part->SetVisibility(true);
    for (auto Part : Hose1Connected) Part->SetVisibility(false);
    for (auto Part : Hose2Connected) Part->SetVisibility(false);
    for (auto& Row : ValveMeshes) Tint(Row.Value, FLinearColor(.45, .45, .45));
    for (auto& Row : ImportedModelActors) SetImportedModelVisibility(Row.Key, true);
    for (auto& Row : Labels) Row.Value->SetText(FText::FromString(Names[Row.Key] + TEXT("\nP -- MPa  T -- C\nInventory -- kg")));
    StatusText->SetText(FText::FromString(TEXT("No active renderer session\nDefault view: photographs in web mode; cameras and detectors hidden")));
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

void AHRSStationActor::SendFeedback(const TSharedPtr<FJsonObject>& Snapshot)
{
    if (!Snapshot || bFeedbackPending || LastSequence == LastFeedbackSequence || CurrentRun.IsEmpty()) return;
    const TArray<TSharedPtr<FJsonValue>>* Rows = nullptr;
    if (!Snapshot->TryGetArrayField(TEXT("equipment"), Rows)) return;
    auto Payload = MakeShared<FJsonObject>();
    Payload->SetStringField(TEXT("run_id"), CurrentRun);
    Payload->SetNumberField(TEXT("generation"), Generation);
    Payload->SetNumberField(TEXT("sequence"), LastSequence);
    TArray<TSharedPtr<FJsonValue>> Equipment;
    for (const auto& Item : *Rows)
    {
        const auto Row = Item->AsObject(); if (!Row) continue;
        const FString Id = Str(Row, TEXT("component_id"));
        if (!Labels.Contains(Id)) continue; // Report only values actually applied to a UE label.
        auto Display = MakeShared<FJsonObject>(); Display->SetStringField(TEXT("component_id"), Id);
        for (const TCHAR* Key : {TEXT("pressure_mpa"), TEXT("temperature_c"), TEXT("mass_kg"), TEXT("flow_g_s")})
        {
            double Value = 0;
            if (Row->TryGetNumberField(Key, Value)) Display->SetNumberField(Key, Value);
            else Display->SetField(Key, MakeShared<FJsonValueNull>());
        }
        Equipment.Add(MakeShared<FJsonValueObject>(Display));
    }
    Payload->SetArrayField(TEXT("equipment"), Equipment);
    FString Body; FJsonSerializer::Serialize(Payload, TJsonWriterFactory<>::Create(&Body));
    const int64 AppliedSequence = LastSequence; const int32 Expected = Generation;
    bFeedbackPending = true; PendingFeedback = FHttpModule::Get().CreateRequest();
    PendingFeedback->SetURL(ApiBase + TEXT("/api/integrations/unreal/session/") + RendererId + TEXT("/feedback"));
    PendingFeedback->SetVerb(TEXT("POST")); PendingFeedback->SetHeader(TEXT("Content-Type"), TEXT("application/json"));
    PendingFeedback->SetTimeout(3.f); PendingFeedback->SetContentAsString(Body);
    TWeakObjectPtr<AHRSStationActor> Weak(this);
    PendingFeedback->OnProcessRequestComplete().BindLambda([Weak, Expected, AppliedSequence](FHttpRequestPtr, FHttpResponsePtr Response, bool bSuccess) {
        if (!Weak.IsValid()) return;
        Weak->bFeedbackPending = false;
        if (Weak->Generation == Expected && bSuccess && Response.IsValid() && Response->GetResponseCode() == 200)
            Weak->LastFeedbackSequence = AppliedSequence;
    });
    if (!PendingFeedback->ProcessRequest()) bFeedbackPending = false;
}

void AHRSStationActor::ApplyAuxiliaryState(const TSharedPtr<FJsonObject>& Safety)
{
    if (!Safety) return;
    const auto Ventilation = Obj(Safety, TEXT("ventilation"));
    const auto Cooling = Obj(Safety, TEXT("cooling"));
    for (const FString Zone : {TEXT("unloading"), TEXT("compressor"), TEXT("storage"), TEXT("dispenser")})
    {
        const auto State = Obj(Ventilation, *Zone);
        UStaticMeshComponent* Mesh = AuxiliaryMeshes.FindRef(TEXT("fan.") + Zone).Get();
        if (Mesh && State)
            Tint(Mesh, Bool(State, TEXT("fault")) ? FLinearColor(.72, .04, .03) :
                 Bool(State, TEXT("running")) ? FLinearColor(.04, .55, .48) : FLinearColor(.35, .4, .42));
    }
    for (const FString Bank : {TEXT("low"), TEXT("medium"), TEXT("high")})
    {
        const auto State = Obj(Cooling, *Bank);
        UStaticMeshComponent* Mesh = AuxiliaryMeshes.FindRef(TEXT("cooling.") + Bank).Get();
        if (Mesh && State)
            Tint(Mesh, Bool(State, TEXT("fault")) ? FLinearColor(.72, .04, .03) :
                 Bool(State, TEXT("running")) ? FLinearColor(.04, .38, .78) : FLinearColor(.35, .4, .42));
    }

    const auto Personnel = Obj(Safety, TEXT("personnel"));
    const auto Evacuated = Obj(Safety, TEXT("evacuated"));
    const auto Restricted = Obj(Safety, TEXT("access_restricted"));
    const auto PowerIsolated = Obj(Safety, TEXT("power_isolated"));
    int32 ZoneIndex = 0;
    for (const FString Zone : {TEXT("unloading"), TEXT("compressor"), TEXT("storage"), TEXT("dispenser")})
    {
        UStaticMeshComponent* Marker = PersonnelMeshes.FindRef(Zone).Get(); if (!Marker) continue;
        const double Present = Num(Personnel, *Zone), Safe = Num(Evacuated, *Zone);
        Marker->SetVisibility(Present > 0 || Safe > 0);
        if (Present > 0)
        {
            const FVector Position = Zone == TEXT("unloading") ? FVector(-1750, -150, 45) :
                Zone == TEXT("compressor") ? FVector(-640, -120, 45) :
                Zone == TEXT("storage") ? FVector(300, -80, 45) : FVector(420, 1020, 45);
            Marker->SetRelativeLocation(Position); Tint(Marker, FLinearColor(.15, .35, .58));
        }
        else if (Safe > 0)
        {
            Marker->SetRelativeLocation(FVector(-1850 + ZoneIndex * 85, 1060, 45));
            Tint(Marker, FLinearColor(.05, .55, .31));
        }
        if (UStaticMeshComponent* Boundary = AuxiliaryMeshes.FindRef(TEXT("access.") + Zone).Get())
            Boundary->SetVisibility(Bool(Restricted, *Zone));
        if (UStaticMeshComponent* Power = AuxiliaryMeshes.FindRef(TEXT("power.") + Zone).Get())
            Tint(Power, Bool(PowerIsolated, *Zone) ? FLinearColor(.12, .16, .18) : FLinearColor(.16, .55, .25));
        ++ZoneIndex;
    }
    const auto Vehicles = Obj(Safety, TEXT("vehicles"));
    if (Vehicles)
    {
        const bool bVehicle1Visible = Num(Vehicles, TEXT("vehicle_1"), 1) > 0;
        const bool bVehicle2Visible = Num(Vehicles, TEXT("vehicle_2"), 1) > 0;
        const bool bTrailerVisible = Num(Vehicles, TEXT("trailer"), 1) > 0;
        if (UStaticMeshComponent* Vehicle = EquipmentMeshes.FindRef(TEXT("vehicle.tank")).Get())
            Vehicle->SetVisibility(!ImportedModelActors.Contains(TEXT("vehicle.tank")) && bVehicle1Visible);
        SetImportedModelVisibility(TEXT("vehicle.tank"), bVehicle1Visible);
        if (UStaticMeshComponent* Vehicle = EquipmentMeshes.FindRef(TEXT("vehicle_2.tank")).Get())
            Vehicle->SetVisibility(!ImportedModelActors.Contains(TEXT("vehicle_2.tank")) && bVehicle2Visible);
        SetImportedModelVisibility(TEXT("vehicle_2.tank"), bVehicle2Visible);
        if (UStaticMeshComponent* Trailer = EquipmentMeshes.FindRef(TEXT("supply")).Get())
            Trailer->SetVisibility(!ImportedModelActors.Contains(TEXT("supply")) && bTrailerVisible);
        SetImportedModelVisibility(TEXT("supply"), bTrailerVisible);
    }
    const auto Recovery = Obj(Safety, TEXT("recovery"));
    if (Recovery && StatusText)
    {
        int32 Completed = 0;
        for (const auto& Item : Recovery->Values)
        {
            bool bPassed = false;
            if (Item.Value.IsValid() && Item.Value->TryGetBool(bPassed) && bPassed) ++Completed;
        }
        StatusText->SetText(FText::FromString(StatusText->Text.ToString() +
            FString::Printf(TEXT("\nRecovery checks %d/%d"), Completed, Recovery->Values.Num())));
    }
    const FString PurgeBank = Str(Safety, TEXT("purge_bank"));
    const auto PurgeFractions = Obj(Safety, TEXT("purge_h2_fraction"));
    const auto Diagnostic = Obj(Safety, TEXT("diagnostic"));
    const FString DiagnosticBank = Str(Diagnostic, TEXT("target"));
    for (const FString Bank : {TEXT("low"), TEXT("medium"), TEXT("high")})
    {
        if (UStaticMeshComponent* Purge = AuxiliaryMeshes.FindRef(TEXT("purge.") + Bank).Get())
        {
            const bool bActive = PurgeBank == Bank;
            Purge->SetVisibility(bActive);
            if (bActive)
            {
                const double Fraction = FMath::Clamp(Num(PurgeFractions, *Bank, 1.0), .005, 1.0);
                Purge->SetRelativeScale3D(FVector(.35, .35, FMath::Max(.25, Fraction) * 2.2));
            }
        }
        if (UStaticMeshComponent* Test = AuxiliaryMeshes.FindRef(TEXT("diagnostic.") + Bank).Get())
            Test->SetVisibility(Diagnostic && DiagnosticBank == Bank);
    }
}

void AHRSStationActor::ApplyProcessState(const TSharedPtr<FJsonObject>& Snapshot)
{
    const auto Activity = Obj(Snapshot, TEXT("process_activity"));
    const auto Settings = Obj(Obj(Snapshot, TEXT("process_operations")), TEXT("settings"));
    bRelativeRisk = Str(Settings, TEXT("risk_display_mode")) != TEXT("absolute");
    auto IsConnected = [Activity, Settings](const TCHAR* Name)
    {
        const auto Row = Obj(Activity, Name);
        const FString State = Str(Row, TEXT("state"));
        const bool bRequested = Settings && Bool(Settings, Name);
        const bool bBlocked = State == TEXT("blocked") || State == TEXT("idle") ||
                              State == TEXT("auto-stopped");
        return Num(Row, TEXT("flow_g_s")) > 1.e-5 || (bRequested && !bBlocked);
    };
    const bool Hose1 = IsConnected(TEXT("vehicle_1"));
    const bool Hose2 = IsConnected(TEXT("vehicle_2"));
    for (auto Part : Hose1Parked) Part->SetVisibility(!Hose1);
    for (auto Part : Hose1Connected) Part->SetVisibility(Hose1);
    for (auto Part : Hose2Parked) Part->SetVisibility(!Hose2);
    for (auto Part : Hose2Connected) Part->SetVisibility(Hose2);
}

void AHRSStationActor::ApplyIncidentState(const TSharedPtr<FJsonObject>& Snapshot)
{
    for (auto& Row : HighlightMeshes) Row.Value->SetVisibility(false);
    for (auto& Row : FireMeshes) Row.Value->SetVisibility(false);
    auto Mark = [this](const FString& Target, bool bFire)
    {
        if (UStaticMeshComponent* Highlight = HighlightMeshes.FindRef(Target).Get()) Highlight->SetVisibility(true);
        if (bFire) if (UStaticMeshComponent* Flame = FireMeshes.FindRef(Target).Get()) Flame->SetVisibility(true);
    };
    const TArray<TSharedPtr<FJsonValue>>* Rows = nullptr;
    if (Snapshot->TryGetArrayField(TEXT("active_faults"), Rows)) for (const auto& Item : *Rows)
    {
        const FString Fault = Item->AsString();
        FString Kind, Target;
        if (Fault.Split(TEXT(":"), &Kind, &Target))
            Mark(Target, Kind.Contains(TEXT("fire")));
    }
    if (Snapshot->TryGetArrayField(TEXT("releases"), Rows)) for (const auto& Item : *Rows)
    {
        const auto Row = Item->AsObject(); if (Row) Mark(Str(Row, TEXT("component_id")), false);
    }
    if (!Snapshot->TryGetArrayField(TEXT("detectors"), Rows)) return;
    for (const auto& Item : *Rows)
    {
        const auto Row = Item->AsObject(); if (!Row) continue;
        const FString Tag = Str(Row, TEXT("sensor_id"));
        const double Value = Num(Row, TEXT("value"));
        const bool bFlame = Tag.StartsWith(TEXT("FD-"));
        const bool bAlarm = bFlame ? Value > .5 : Value >= .4;
        if (UStaticMeshComponent* Marker = DetectorMeshes.FindRef(Tag).Get())
            Tint(Marker, bAlarm ? FLinearColor(.8, .035, .02) :
                 bFlame ? FLinearColor(.94, .41, .08) : FLinearColor(.05, .55, .62));
        if (!bAlarm) continue;
        const FString Node = Tag.Mid(3, 2);
        const FString Target = Node == TEXT("01") || Node == TEXT("02") ? TEXT("supply") :
            Node == TEXT("06") || Node == TEXT("21") ? TEXT("compressor") :
            Node == TEXT("07") ? TEXT("cascade.low") : Node == TEXT("08") ? TEXT("cascade.medium") :
            Node == TEXT("09") ? TEXT("cascade.high") : Node == TEXT("10") ? TEXT("header") :
            Node == TEXT("13") || Node == TEXT("23") ? TEXT("dispenser.hose") :
            Node == TEXT("17") ? TEXT("dispenser_2.hose") : Node == TEXT("19") ? TEXT("cooler") :
            Node == TEXT("20") ? TEXT("vent") : FString();
        if (!Target.IsEmpty()) Mark(Target, bFlame);
    }
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
    StatusText->SetText(FText::FromString(FString::Printf(TEXT("Simulation %.1f s | %s | %s\n1/2/3 select | X inlet | Z outlet | E ESD | F stop\nR risk | D distance | C cameras | G detectors"),
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
    ApplyAuxiliaryState(Obj(Snapshot, TEXT("safety")));
    ApplyProcessState(Snapshot);
    ApplyIncidentState(Snapshot);
    ApplyRisk(Obj(Snapshot, TEXT("risk_zones")));
    SendFeedback(Snapshot);
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
        const double Score = Num(Row, bRelativeRisk ? TEXT("relative_score") : TEXT("absolute_score"));
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
void AHRSStationActor::ToggleCameras()
{
    bShowCameras = !bShowCameras;
    for (auto& Row : CameraMeshes) Row.Value->SetVisibility(bShowCameras);
}
void AHRSStationActor::ToggleDetectors()
{
    bShowDetectors = !bShowDetectors;
    for (auto& Row : DetectorMeshes) Row.Value->SetVisibility(bShowDetectors);
}

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
    if (PendingFeedback) PendingFeedback->CancelRequest();
    Super::EndPlay(Reason);
}
