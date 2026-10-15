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
    const TCHAR* Cone = TEXT("/Engine/BasicShapes/Cone.Cone");
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
    const FVector& Size, const FLinearColor& Color, bool bTransparent, const FString& ComponentId,
    float Metallic, float Roughness, float Specular)
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
    UMaterialInterface* Base = bTransparent ? TransparentMaterial.Get() : PhysicalMaterial.Get();
    if (!Base) Base = OpaqueMaterial.Get();
    if (Base)
    {
        auto* Dynamic = UMaterialInstanceDynamic::Create(Base, this);
        Dynamic->SetVectorParameterValue(TEXT("Color"), Color);
        if (!bTransparent)
        {
            Dynamic->SetScalarParameterValue(TEXT("Metallic"), Metallic);
            Dynamic->SetScalarParameterValue(TEXT("Roughness"), Roughness);
            Dynamic->SetScalarParameterValue(TEXT("Specular"), Specular);
        }
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
    FireMeshes.Add(Id, Shape(Cone, Origin + FVector(0, 0, 345), FVector(65, 65, 220),
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
    // Equipment decomposition follows public H2Tools/NREL reference-station
    // practice and the owner's de-identified industrial photographs.  It is a
    // visual reference only and does not represent vendor CAD.
    Shape(Cube, FVector(-400, -100, -20), FVector(4800, 2800, 40),
          FLinearColor(.49, .54, .55), false, FString(), .02f, .96f, .25f);
    Shape(Cube, FVector(-350, 900, 2), FVector(4700, 520, 8),
          FLinearColor(.075, .085, .09), false, FString(), .01f, .91f, .2f);
    for (int32 X = -2500; X <= 1700; X += 500)
        Shape(Cube, FVector(X, 900, 8), FVector(220, 9, 3), FLinearColor(.83, .82, .68), false, FString(), .01f, .72f, .25f);
    // Concrete construction joints, kerbs, drains and vehicle approach markings.
    for (int32 X = -2600; X <= 1800; X += 400)
        Shape(Cube, FVector(X, -220, 2), FVector(2, 1760, 2), FLinearColor(.20, .23, .23), false, FString(), .02f, .9f, .2f);
    for (int32 Y = -1000; Y <= 600; Y += 400)
        Shape(Cube, FVector(-400, Y, 2), FVector(4400, 2, 2), FLinearColor(.20, .23, .23), false, FString(), .02f, .9f, .2f);
    for (float X : {-2650.f, 1900.f})
        Shape(Cube, FVector(X, 0, 14), FVector(24, 2100, 28), FLinearColor(.66, .68, .66), false, FString(), .04f, .87f, .28f);
    for (float X : {-100.f, 700.f})
        for (int32 Y = 180; Y <= 780; Y += 80)
            Shape(Cube, FVector(X, Y, 8), FVector(9, 42, 3), FLinearColor(.82, .82, .76), false, FString(), .01f, .74f, .2f);
    for (int32 Y = 250; Y <= 760; Y += 64)
        Shape(Cube, FVector(1450, Y, 8), FVector(180, 18, 3), FLinearColor(.16, .19, .2), false, FString(), .15f, .65f, .35f);

    // Road furniture and wear break up the perfectly uniform test-pad look.
    // These are generic visual cues, kept clear of the operational envelopes.
    for (int32 X = -2360; X <= 1560; X += 560)
    {
        auto* Patch = Shape(Cube, FVector(X, 900 + ((X / 280) % 2) * 38, 6),
            FVector(310, 190, 2), FLinearColor(.055, .061, .064), false,
            FString(), .015f, .97f, .18f);
        Patch->SetRelativeRotation(FRotator(0, (X / 80) % 5 - 2, 0));
    }
    for (float X : {-1560.f, 1540.f})
        for (int32 Y = 690; Y <= 1110; Y += 70)
            Shape(Cube, FVector(X, Y, 10), FVector(34, 48, 3),
                FLinearColor(.88, .87, .74), false, FString(), .01f, .70f, .22f);
    // Stop bars, directional arrow and recessed drainage/manhole details.
    Shape(Cube, FVector(-1270, 900, 10), FVector(22, 430, 4),
        FLinearColor(.88, .87, .76), false, FString(), .01f, .66f, .22f);
    Shape(Cube, FVector(1240, 900, 10), FVector(22, 430, 4),
        FLinearColor(.88, .87, .76), false, FString(), .01f, .66f, .22f);
    Shape(Cube, FVector(-360, 900, 10), FVector(260, 24, 3),
        FLinearColor(.84, .83, .70), false, FString(), .01f, .71f, .22f);
    for (float Sign : {-1.f, 1.f})
    {
        auto* Arrow = Shape(Cube, FVector(-235 + Sign * 8, 900 + Sign * 55, 10),
            FVector(120, 22, 3), FLinearColor(.84, .83, .70), false,
            FString(), .01f, .71f, .22f);
        Arrow->SetRelativeRotation(FRotator(0, Sign * 42, 0));
    }
    for (float X : {-2050.f, -840.f, 630.f, 1700.f})
    {
        auto* Cover = Shape(Cylinder, FVector(X, 1040, 9), FVector(42, 42, 4),
            FLinearColor(.12, .135, .14), false, FString(), .55f, .82f, .32f);
        for (float Offset : {-18.f, 0.f, 18.f})
            Shape(Cube, FVector(X + Offset, 1040, 13), FVector(3, 62, 2),
                FLinearColor(.23, .25, .25), false, FString(), .45f, .70f, .36f);
    }

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
        FireMeshes.Add(Id, Shape(Cone, Origin + FVector(0, 0, Envelope.Z + 100),
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
    for (const FVector VehicleOrigin : {FVector(280, 700, 0), FVector(1080, 700, 0)})
    {
        for (float Y : {-52.f, 0.f, 52.f})
        {
            auto* Tank = Shape(Cylinder, VehicleOrigin + FVector(-25, Y, 68), FVector(43, 43, 310),
                               FLinearColor(.12, .18, .22), false,
                               VehicleOrigin.X < 500 ? TEXT("vehicle.tank") : TEXT("vehicle_2.tank"), .38f, .28f, .5f);
            Tank->SetRelativeRotation(FRotator(0, 90, 0)); Tank->SetVisibility(false);
            VehicleTankCutawayMeshes.Add(Tank);
        }
    }
    AddEquipment(TEXT("vent"), TEXT("VENT STACK"), FVector(1400, -900, 0),
                 FVector(100, 100, 600), FLinearColor(.58, .64, .65));
    AddEquipment(TEXT("dispenser.hose"), TEXT("HOSE 1"), FVector(180, 520, 0),
                 FVector(240, 200, 100), FLinearColor(.08, .1, .11));
    AddEquipment(TEXT("dispenser_2.hose"), TEXT("HOSE 2"), FVector(980, 520, 0),
                 FVector(240, 200, 100), FLinearColor(.08, .1, .11));
    EquipmentMeshes[TEXT("dispenser.hose")]->SetVisibility(false);
    EquipmentMeshes[TEXT("dispenser_2.hose")]->SetVisibility(false);

    // Hide primitive envelopes where detailed procedural equipment replaces
    // them.  Dimensions, selection and risk overlays remain unchanged.
    EquipmentMeshes[TEXT("header")]->SetVisibility(false);
    EquipmentMeshes[TEXT("vent")]->SetVisibility(false);

    const FLinearColor Stainless(.61, .66, .67);
    const FLinearColor DarkSteel(.15, .19, .20);
    const FLinearColor StationBlue(.025, .25, .48);
    const FLinearColor SafetyYellow(.92, .66, .04);
    const FLinearColor InstrumentBlue(.08, .30, .48);
    const FLinearColor ScreenBlack(.012, .018, .022);

    auto AddGauge = [this, &Stainless, &ScreenBlack](const FVector& Position, const FString& ComponentId)
    {
        auto* Case = Shape(Cylinder, Position, FVector(23, 23, 11), Stainless, false, ComponentId, .82f, .24f, .55f);
        Case->SetRelativeRotation(FRotator(90, 0, 0));
        auto* Face = Shape(Cylinder, Position + FVector(0, -6, 0), FVector(19, 19, 3), FLinearColor(.91, .91, .84), false, ComponentId, .02f, .34f, .45f);
        Face->SetRelativeRotation(FRotator(90, 0, 0));
        Segment(Position + FVector(0, -9, 0), Position + FVector(8, -10, 7), 1.5f, ScreenBlack, false, ComponentId);
    };

    // Stainless common-header skid with instruments, supports and manual valves.
    for (float X : {160.f, 300.f, 440.f})
    {
        Segment(FVector(X, -345, 55), FVector(X, -255, 55), 11, Stainless, false, TEXT("header"));
        Segment(FVector(X, -300, 55), FVector(X, -300, 126), 8, Stainless, false, TEXT("header"));
        AddGauge(FVector(X, -300, 145), TEXT("header"));
        auto* Wheel = Shape(Cylinder, FVector(X, -300, 95), FVector(19, 19, 5), FLinearColor(.68, .10, .045), false, TEXT("header"), .26f, .48f, .42f);
        Wheel->SetRelativeRotation(FRotator(90, 0, 0));
    }
    Segment(FVector(120, -300, 55), FVector(480, -300, 55), 13, Stainless, false, TEXT("header"));
    for (float X : {120.f, 480.f})
        Shape(Cube, FVector(X, -300, 35), FVector(14, 90, 70), DarkSteel, false, TEXT("header"), .7f, .39f, .5f);
    Shape(Cube, FVector(300, -350, 94), FVector(330, 12, 54), FLinearColor(.82, .85, .83), false, TEXT("header"), .25f, .42f, .45f);

    // H70 dispensers: plinth, cabinet, display, E-stop, nozzle dock and top cap.
    for (const auto& Pair : TArray<TPair<FString, FVector>>{
        TPair<FString, FVector>(TEXT("dispenser.pcv"), FVector(0, 420, 0)),
        TPair<FString, FVector>(TEXT("dispenser_2.pcv"), FVector(800, 420, 0))})
    {
        const FString& Id = Pair.Key; const FVector O = Pair.Value;
        Shape(Cube, O + FVector(0, 0, 8), FVector(150, 130, 16), DarkSteel, false, Id, .65f, .38f, .5f);
        Shape(Cube, O + FVector(0, 0, 225), FVector(132, 112, 18), FLinearColor(.88, .90, .89), false, Id, .24f, .36f, .45f);
        Shape(Cube, O + FVector(0, -57, 158), FVector(82, 4, 46), ScreenBlack, false, Id, .04f, .23f, .6f);
        Shape(Cube, O + FVector(0, -60, 119), FVector(92, 3, 16), StationBlue, false, Id, .18f, .32f, .5f);
        Shape(Cylinder, O + FVector(39, -61, 91), FVector(13, 13, 8), FLinearColor(.76, .035, .02), false, Id, .18f, .45f, .45f)->SetRelativeRotation(FRotator(90, 0, 0));
        Shape(Cube, O + FVector(-53, -59, 106), FVector(19, 8, 42), DarkSteel, false, Id, .65f, .35f, .52f);
        Shape(Cylinder, O + FVector(-53, -68, 106), FVector(8, 8, 34), Stainless, false, Id, .84f, .22f, .55f)->SetRelativeRotation(FRotator(90, 0, 0));
        for (float X : {-45.f, 45.f})
            Shape(Cube, O + FVector(X, -60, 33), FVector(5, 4, 40), FLinearColor(.55, .58, .57), false, Id, .32f, .5f, .4f);
    }

    // Tripod-supported vent header and elevated discharge stack.
    Segment(FVector(1400, -900, 25), FVector(1400, -900, 650), 14, Stainless, false, TEXT("vent"));
    Segment(FVector(1380, -900, 620), FVector(1420, -900, 620), 9, Stainless, false, TEXT("vent"));
    Segment(FVector(1400, -900, 650), FVector(1400, -900, 690), 22, DarkSteel, false, TEXT("vent"));
    for (float Angle : {0.f, 120.f, 240.f})
    {
        const float R = FMath::DegreesToRadians(Angle);
        const FVector Foot(1400 + 82 * FMath::Cos(R), -900 + 82 * FMath::Sin(R), 15);
        Segment(Foot, FVector(1400, -900, 360), 7, DarkSteel, false, TEXT("vent"));
        Shape(Cube, Foot, FVector(34, 34, 10), Stainless, false, TEXT("vent"), .68f, .35f, .5f);
    }
    for (float Z : {180.f, 360.f, 540.f})
        Shape(Cylinder, FVector(1400, -900, Z), FVector(38, 38, 5), DarkSteel, false, TEXT("vent"), .68f, .34f, .5f);

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

    // Cutaway-only internals. These are schematic equipment packages tied to
    // the same process nodes; they add no duplicate physics calculations.
    auto AddServiceInterior = [this](UStaticMeshComponent* Mesh)
    {
        if (Mesh) { Mesh->SetVisibility(false); ServiceInteriorMeshes.Add(Mesh); }
        return Mesh;
    };
    auto* Motor = AddServiceInterior(Shape(Cylinder, FVector(-735, -600, 92), FVector(72, 72, 180),
        InstrumentBlue, false, TEXT("compressor"), .62f, .30f, .52f));
    Motor->SetRelativeRotation(FRotator(0, 90, 0));
    for (int32 Stage = 0; Stage < 3; ++Stage)
    {
        const FVector StageOrigin(-575 + Stage * 72, -600, 90 + Stage * 42);
        AddServiceInterior(Shape(Cylinder, StageOrigin, FVector(52 - Stage * 8, 52 - Stage * 8, 92),
            Stainless, false, TEXT("compressor"), .72f, .24f, .55f));
        AddServiceInterior(Segment(StageOrigin + FVector(0, 0, 45), StageOrigin + FVector(0, 0, 105),
            9, Stainless, false, TEXT("compressor")));
    }
    AddServiceInterior(Segment(FVector(-820, -600, 70), FVector(-420, -600, 70),
        12, Stainless, false, TEXT("compressor")));
    auto* Hx = AddServiceInterior(Shape(Cylinder, FVector(1050, -600, 112), FVector(80, 80, 260),
        Stainless, false, TEXT("cooler"), .76f, .22f, .55f));
    Hx->SetRelativeRotation(FRotator(0, 90, 0));
    for (float X : {940.f, 990.f, 1040.f, 1090.f, 1140.f})
        AddServiceInterior(Shape(Cube, FVector(X, -600, 112), FVector(4, 175, 170),
            InstrumentBlue, false, TEXT("cooler"), .45f, .34f, .5f));
    AddServiceInterior(Shape(Cylinder, FVector(1190, -600, 72), FVector(74, 74, 105),
        DarkSteel, false, TEXT("cooler"), .66f, .30f, .5f));
    AddServiceInterior(Segment(FVector(920, -600, 55), FVector(1220, -600, 55),
        10, Stainless, false, TEXT("cooler")));

    // Canopy: separate roof deck, fascia and trim.  Every parallel surface has
    // a physical gap, preventing the coplanar depth fighting seen at corners.
    CanopyCutawayMeshes.Add(Shape(Cube, FVector(420, 565, 505), FVector(1900, 900, 24), FLinearColor(.79, .82, .82), false, FString(), .55f, .34f, .47f));
    for (float Y : {1030.f, 100.f})
    {
        CanopyCutawayMeshes.Add(Shape(Cube, FVector(420, Y, 480), FVector(1848, 22, 74), FLinearColor(.88, .90, .89), false, FString(), .23f, .42f, .44f));
        Shape(Cube, FVector(420, Y + (Y > 500 ? 13 : -13), 479), FVector(1852, 7, 16), StationBlue, false, FString(), .20f, .35f, .50f);
    }
    for (float X : {-530.f, 1370.f})
    {
        CanopyCutawayMeshes.Add(Shape(Cube, FVector(X, 565, 480), FVector(22, 878, 74), FLinearColor(.88, .90, .89), false, FString(), .23f, .42f, .44f));
        Shape(Cube, FVector(X + (X > 0 ? 13 : -13), 565, 479), FVector(7, 882, 16), StationBlue, false, FString(), .20f, .35f, .50f);
    }
    for (float X : {-450.f, 420.f, 1290.f}) for (float Y : {180.f, 950.f})
    {
        Shape(Cube, FVector(X, Y, 245), FVector(25, 25, 490), FLinearColor(.64, .68, .68), false, FString(), .72f, .28f, .52f);
        Shape(Cube, FVector(X, Y, 10), FVector(72, 72, 18), FLinearColor(.53, .55, .54), false, FString(), .62f, .42f, .46f);
        for (float DX : {-24.f, 24.f}) for (float DY : {-24.f, 24.f})
            Shape(Cylinder, FVector(X + DX, Y + DY, 24), FVector(5, 5, 11), DarkSteel, false, FString(), .78f, .27f, .52f);
    }
    for (float Y : {230.f, 565.f, 900.f})
        Shape(Cube, FVector(420, Y, 476), FVector(1810, 14, 24), DarkSteel, false, FString(), .72f, .34f, .50f);
    for (float X = -350; X <= 1190; X += 385)
        for (float Y : {330.f, 800.f})
            Shape(Cube, FVector(X, Y, 464), FVector(190, 54, 7), FLinearColor(.89, .91, .88), false, FString(), .12f, .48f, .42f);
    // Gutter and downpipes are separated from the fascia by 18 mm-equivalent.
    Segment(FVector(-500, 100, 452), FVector(1340, 100, 452), 9, DarkSteel);
    Segment(FVector(-500, 100, 452), FVector(-500, 100, 42), 8, DarkSteel);
    Segment(FVector(1340, 100, 452), FVector(1340, 100, 42), 8, DarkSteel);

    // Operations/utility room with roof cap, door, glazing, louvres and outdoor unit.
    Shape(Cube, FVector(-1000, 500, 150), FVector(560, 520, 300), FLinearColor(.77, .80, .79), false, FString(), .18f, .68f, .34f);
    Shape(Cube, FVector(-1000, 500, 314), FVector(590, 550, 28), FLinearColor(.54, .58, .58), false, FString(), .56f, .39f, .48f);
    // Panel joints, base flashing, parapet, gutter and downpipe make the room
    // read as a fabricated industrial building instead of a single box.
    for (float X = -1240; X <= -760; X += 80)
        Shape(Cube, FVector(X, 235, 150), FVector(3, 5, 288),
            FLinearColor(.50, .54, .54), false, FString(), .50f, .55f, .38f);
    for (float Y = 300; Y <= 700; Y += 80)
        Shape(Cube, FVector(-1283, Y, 150), FVector(5, 3, 288),
            FLinearColor(.50, .54, .54), false, FString(), .50f, .55f, .38f);
    Shape(Cube, FVector(-1000, 500, 18), FVector(580, 540, 30),
        FLinearColor(.32, .35, .35), false, FString(), .28f, .82f, .31f);
    for (float X : {-1287.f, -713.f})
        Shape(Cube, FVector(X, 500, 333), FVector(10, 558, 38),
            FLinearColor(.44, .48, .48), false, FString(), .57f, .38f, .48f);
    for (float Y : {223.f, 777.f})
        Shape(Cube, FVector(-1000, Y, 333), FVector(584, 10, 38),
            FLinearColor(.44, .48, .48), false, FString(), .57f, .38f, .48f);
    Segment(FVector(-1272, 230, 310), FVector(-728, 230, 310), 8, DarkSteel);
    Segment(FVector(-1272, 230, 310), FVector(-1272, 230, 28), 7, DarkSteel);
    Shape(Cube, FVector(-1120, 230, 126), FVector(115, 12, 226), StationBlue, false, FString(), .18f, .38f, .48f);
    Shape(Cube, FVector(-1120, 222, 126), FVector(132, 7, 242),
        FLinearColor(.12, .16, .17), false, FString(), .50f, .38f, .48f);
    Shape(Cylinder, FVector(-1082, 214, 125), FVector(7, 7, 8),
        FLinearColor(.72, .74, .70), false, FString(), .78f, .24f, .54f)->SetRelativeRotation(FRotator(90, 0, 0));
    Shape(Cube, FVector(-1120, 205, 260), FVector(170, 55, 14),
        FLinearColor(.40, .44, .44), false, FString(), .58f, .38f, .46f);
    Shape(Cube, FVector(-870, 230, 180), FVector(210, 10, 92), FLinearColor(.08, .15, .18), false, FString(), .08f, .18f, .62f);
    Shape(Cube, FVector(-870, 223, 180), FVector(190, 3, 72), FLinearColor(.22, .39, .46), true);
    for (float X : {-958.f, -870.f, -782.f})
        Shape(Cube, FVector(X, 214, 180), FVector(4, 5, 94),
            FLinearColor(.48, .53, .53), false, FString(), .62f, .33f, .48f);
    for (float Z = 82; Z <= 218; Z += 22)
        Shape(Cube, FVector(-1278, 500, Z), FVector(7, 280, 8), DarkSteel, false, FString(), .68f, .38f, .48f);
    Shape(Cube, FVector(-1288, 735, 112), FVector(14, 100, 160),
        FLinearColor(.68, .70, .67), false, FString(), .32f, .55f, .42f);
    Shape(Cube, FVector(-1296, 735, 126), FVector(4, 72, 72),
        FLinearColor(.06, .09, .10), false, FString(), .10f, .28f, .60f);
    Shape(Cylinder, FVector(-1300, 700, 172), FVector(8, 8, 5),
        FLinearColor(.86, .10, .035), false, FString(), .18f, .34f, .52f)->SetRelativeRotation(FRotator(90, 0, 0));
    Shape(Cube, FVector(-690, 500, 92), FVector(76, 130, 160), FLinearColor(.72, .75, .74), false, FString(), .28f, .52f, .42f);
    Shape(Cylinder, FVector(-651, 500, 92), FVector(48, 48, 12), DarkSteel, false, FString(), .45f, .42f, .44f)->SetRelativeRotation(FRotator(0, 90, 0));
    for (float Angle = 0; Angle < 360; Angle += 45)
    {
        const float R = FMath::DegreesToRadians(Angle);
        Segment(FVector(-650, 500, 92), FVector(-650, 500 + 34 * FMath::Cos(R), 92 + 34 * FMath::Sin(R)),
            3, FLinearColor(.46, .49, .48));
    }
    Shape(Cube, FVector(-1000, 210, 24), FVector(260, 52, 16),
        FLinearColor(.40, .42, .40), false, FString(), .04f, .90f, .25f);

    // Landscaping and site furniture establish human scale around the plant.
    auto AddTree = [this](const FVector& Base, float Scale, const FLinearColor& Crown)
    {
        const FLinearColor Bark(.25, .15, .075);
        Shape(Cylinder, Base + FVector(0, 0, 72 * Scale),
            FVector(18 * Scale, 18 * Scale, 144 * Scale), Bark, false,
            FString(), .02f, .93f, .22f);
        Shape(Sphere, Base + FVector(-25 * Scale, 0, 168 * Scale),
            FVector(70 * Scale), Crown, false, FString(), .01f, .90f, .20f);
        Shape(Sphere, Base + FVector(30 * Scale, 8 * Scale, 184 * Scale),
            FVector(78 * Scale), Crown * FLinearColor(.86, .95, .82), false,
            FString(), .01f, .88f, .20f);
        Shape(Sphere, Base + FVector(0, -28 * Scale, 218 * Scale),
            FVector(64 * Scale), Crown * FLinearColor(.76, .90, .74), false,
            FString(), .01f, .89f, .20f);
    };
    Shape(Cube, FVector(-400, -1270, 10), FVector(4300, 180, 20),
        FLinearColor(.22, .31, .14), false, FString(), .01f, .98f, .18f);
    for (int32 Index = 0; Index < 11; ++Index)
        AddTree(FVector(-2440 + Index * 410, -1270 + (Index % 2) * 22, 18),
            .72f + .08f * (Index % 3),
            FLinearColor(.18 + .02 * (Index % 2), .36 + .025 * (Index % 3), .11));
    for (float X : {-1480.f, -1320.f})
    {
        Shape(Cube, FVector(X, 620, 24), FVector(120, 120, 48),
            FLinearColor(.36, .38, .35), false, FString(), .10f, .86f, .28f);
        Shape(Cube, FVector(X, 620, 51), FVector(108, 108, 12),
            FLinearColor(.16, .20, .10), false, FString(), .01f, .98f, .16f);
        for (float DX : {-30.f, 0.f, 30.f})
            Shape(Sphere, FVector(X + DX, 620, 88 + FMath::Abs(DX) * .2f), FVector(38),
                FLinearColor(.12, .38, .16), false, FString(), .01f, .90f, .20f);
    }

    // Entrance lighting and a simple hydrogen-molecule sculpture form a
    // memorable landmark without copying any real facility identity.
    for (float X : {-1550.f, 1720.f})
    {
        Segment(FVector(X, 1110, 20), FVector(X, 1110, 330), 12,
            FLinearColor(.18, .21, .21));
        Shape(Cube, FVector(X + 26, 1110, 330), FVector(70, 28, 18),
            FLinearColor(.72, .75, .72), false, FString(), .50f, .30f, .48f);
        Shape(Cube, FVector(X + 28, 1110, 318), FVector(54, 20, 5),
            FLinearColor(.92, .84, .55), true);
    }
    const FVector SculptureBase(-1510, 790, 0);
    Shape(Cube, SculptureBase + FVector(0, 0, 25), FVector(210, 140, 50),
        FLinearColor(.44, .47, .46), false, FString(), .32f, .72f, .34f);
    Shape(Cube, SculptureBase + FVector(0, 0, 58), FVector(180, 110, 16),
        FLinearColor(.68, .71, .69), false, FString(), .42f, .40f, .44f);
    const FVector H1 = SculptureBase + FVector(-46, 0, 142);
    const FVector H2 = SculptureBase + FVector(48, 0, 204);
    Segment(H1, H2, 18, FLinearColor(.72, .75, .74));
    Shape(Sphere, H1, FVector(48), FLinearColor(.02, .36, .62), false, FString(), .30f, .24f, .56f);
    Shape(Sphere, H2, FVector(48), FLinearColor(.02, .52, .48), false, FString(), .30f, .24f, .56f);
    Text(SculptureBase + FVector(0, -75, 54), TEXT("H2"), 22);

    // Open steel perimeter fence with posts and rails instead of opaque walls.
    for (float Y : {-1120.f, 1120.f})
    {
        for (float X = -2720; X <= 1920; X += 240)
            Shape(Cube, FVector(X, Y, 108), FVector(12, 12, 216), DarkSteel, false, FString(), .72f, .42f, .48f);
        for (float Z : {38.f, 108.f, 178.f})
            Shape(Cube, FVector(-400, Y, Z), FVector(4640, 7, 7), DarkSteel, false, FString(), .72f, .42f, .48f);
    }
    for (float X : {-2720.f, 1920.f})
    {
        for (float Y = -1120; Y <= 1120; Y += 240)
            Shape(Cube, FVector(X, Y, 108), FVector(12, 12, 216), DarkSteel, false, FString(), .72f, .42f, .48f);
        for (float Z : {38.f, 108.f, 178.f})
            Shape(Cube, FVector(X, 0, Z), FVector(7, 2240, 7), DarkSteel, false, FString(), .72f, .42f, .48f);
    }

    // Pipe corridor uses stainless process tube on galvanized supports; yellow
    // marks trailer supply and green marks the station high-pressure header.
    Segment(FVector(-2200, -550, 78), FVector(-900, -550, 78), 15, FLinearColor(.72, .54, .055), false, FString());
    Segment(FVector(-900, -550, 78), FVector(-900, -300, 78), 15, FLinearColor(.72, .54, .055), false, FString());
    Segment(FVector(-900, -300, 78), FVector(1350, -300, 78), 15, FLinearColor(.035, .43, .35), false, FString());
    Segment(FVector(-900, -275, 104), FVector(1350, -275, 104), 8, Stainless, false, FString());
    for (float X = -850; X <= 1300; X += 215)
    {
        Shape(Cube, FVector(X, -288, 43), FVector(13, 95, 86), DarkSteel, false, FString(), .7f, .42f, .48f);
        Shape(Cube, FVector(X, -288, 89), FVector(13, 112, 8), DarkSteel, false, FString(), .7f, .42f, .48f);
    }

    // Vehicle-impact protection and zone edge markings.
    for (float X : {-120.f, 120.f, 680.f, 920.f})
        for (float Y : {300.f, 545.f})
            Shape(Cylinder, FVector(X, Y, 46), FVector(16, 16, 92), SafetyYellow, false, FString(), .16f, .51f, .45f);
    for (float X : {-920.f, -760.f, 980.f, 1180.f})
        Shape(Cylinder, FVector(X, -360, 48), FVector(16, 16, 96), SafetyYellow, false, FString(), .16f, .51f, .45f);

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
        const FLinearColor LensColor = bFlame ? FLinearColor(.94, .41, .08) : FLinearColor(.05, .55, .62);
        // A compact weatherproof detector head: swivel bracket, cylindrical
        // housing, sun shield and coloured optical/sampling face.  The front
        // lens remains the state-bearing component so alarm tinting stays
        // unambiguous while the surrounding hardware reads as real equipment.
        auto* Marker = Shape(Cylinder, Entry.Value, FVector(22, 22, 12),
                             bFlame ? FLinearColor(.94, .41, .08) : FLinearColor(.05, .55, .62),
                             false, Entry.Key, .28f, .27f, .58f);
        Marker->SetRelativeRotation(FRotator(90, 0, 0));
        auto AttachDetectorPart = [Marker](UStaticMeshComponent* Part)
        {
            Part->AttachToComponent(Marker, FAttachmentTransformRules::KeepWorldTransform);
            Part->SetVisibility(false);
        };
        AttachDetectorPart(Shape(Cylinder, Entry.Value + FVector(0, -8, 0), FVector(16, 16, 4),
            LensColor, false, Entry.Key + TEXT(".lens"), .06f, .16f, .68f));
        AttachDetectorPart(Shape(Cube, Entry.Value + FVector(0, 0, 17), FVector(38, 34, 5),
            FLinearColor(.80, .83, .82), false, Entry.Key + TEXT(".shield"), .63f, .30f, .48f));
        AttachDetectorPart(Shape(Cube, Entry.Value + FVector(0, 12, -14), FVector(9, 25, 27),
            DarkSteel, false, Entry.Key + TEXT(".bracket"), .72f, .34f, .50f));
        AttachDetectorPart(Shape(Cylinder, Entry.Value + FVector(0, 25, -25), FVector(7, 7, 16),
            Stainless, false, Entry.Key + TEXT(".mount"), .78f, .28f, .52f));
        Marker->SetVisibility(false, true); DetectorMeshes.Add(Entry.Key, Marker);
    }
    const TArray<TPair<FString, FVector>> Cameras = {
        TPair<FString, FVector>(TEXT("CAM-01"), FVector(300, -360, 340)), TPair<FString, FVector>(TEXT("CAM-02"), FVector(-620, -380, 310)),
        TPair<FString, FVector>(TEXT("CAM-03"), FVector(410, 325, 360)), TPair<FString, FVector>(TEXT("CAM-04"), FVector(1350, -330, 300)),
        TPair<FString, FVector>(TEXT("CAM-05"), FVector(-2200, 120, 380))
    };
    for (const auto& Entry : Cameras)
    {
        // Bullet CCTV assembly with visor, dark lens, cable gland and a
        // two-link galvanized wall bracket.  A slight downward pitch makes
        // the coverage direction legible from the operator camera.
        auto* Camera = Shape(Cylinder, Entry.Value, FVector(30, 30, 72),
            FLinearColor(.76, .80, .80), false, Entry.Key, .62f, .31f, .52f);
        Camera->SetRelativeRotation(FRotator(0, 90, 0));
        auto AttachCameraPart = [Camera](UStaticMeshComponent* Part)
        {
            Part->AttachToComponent(Camera, FAttachmentTransformRules::KeepWorldTransform);
            Part->SetVisibility(false);
        };
        auto* Lens = Shape(Cylinder, Entry.Value + FVector(38, 0, 0), FVector(23, 23, 7),
            ScreenBlack, false, Entry.Key + TEXT(".lens"), .08f, .12f, .70f);
        Lens->SetRelativeRotation(FRotator(0, 90, 0)); AttachCameraPart(Lens);
        AttachCameraPart(Shape(Cube, Entry.Value + FVector(11, 0, 21), FVector(82, 46, 7),
            FLinearColor(.70, .74, .74), false, Entry.Key + TEXT(".visor"), .55f, .34f, .50f));
        AttachCameraPart(Shape(Cylinder, Entry.Value + FVector(-40, 0, -6), FVector(10, 10, 20),
            DarkSteel, false, Entry.Key + TEXT(".gland"), .55f, .36f, .50f));
        AttachCameraPart(Segment(Entry.Value + FVector(-36, 0, -12), Entry.Value + FVector(-36, 0, -55),
            8, Stainless, false, Entry.Key + TEXT(".arm")));
        AttachCameraPart(Segment(Entry.Value + FVector(-36, 0, -55), Entry.Value + FVector(-70, 0, -55),
            8, Stainless, false, Entry.Key + TEXT(".arm")));
        AttachCameraPart(Shape(Cube, Entry.Value + FVector(-76, 0, -55), FVector(8, 45, 45),
            DarkSteel, false, Entry.Key + TEXT(".plate"), .68f, .36f, .50f));
        Camera->SetRelativeRotation(FRotator(-10, 0, 0));
        Camera->SetVisibility(false, true); CameraMeshes.Add(Entry.Key, Camera);
    }

    auto AddPerson = [this](const FVector& TorsoPosition, const FLinearColor& VestColor,
        const FString& ComponentId, bool bHardHat)
    {
        const FLinearColor Trousers(.075, .10, .12);
        const FLinearColor Skin(.62, .42, .29);
        auto* Torso = Shape(Cube, TorsoPosition, FVector(38, 25, 62), VestColor,
            false, ComponentId, .01f, .82f, .24f);
        auto Attach = [Torso](UStaticMeshComponent* Part)
        { Part->AttachToComponent(Torso, FAttachmentTransformRules::KeepWorldTransform); };
        Attach(Shape(Sphere, TorsoPosition + FVector(0, 0, 50), FVector(19),
            Skin, false, ComponentId + TEXT(".head"), .01f, .83f, .24f));
        Attach(Segment(TorsoPosition + FVector(-13, 0, -24), TorsoPosition + FVector(-15, 1, -82),
            13, Trousers, false, ComponentId + TEXT(".leg")));
        Attach(Segment(TorsoPosition + FVector(13, 0, -24), TorsoPosition + FVector(15, -1, -82),
            13, Trousers, false, ComponentId + TEXT(".leg")));
        Attach(Shape(Cube, TorsoPosition + FVector(-15, -2, -84), FVector(18, 38, 10),
            FLinearColor(.035, .045, .05), false, ComponentId + TEXT(".boot"), .02f, .74f, .28f));
        Attach(Shape(Cube, TorsoPosition + FVector(15, -2, -84), FVector(18, 38, 10),
            FLinearColor(.035, .045, .05), false, ComponentId + TEXT(".boot"), .02f, .74f, .28f));
        Attach(Segment(TorsoPosition + FVector(-21, 0, 19), TorsoPosition + FVector(-29, 3, -25),
            10, VestColor, false, ComponentId + TEXT(".arm")));
        Attach(Segment(TorsoPosition + FVector(21, 0, 19), TorsoPosition + FVector(29, -3, -25),
            10, VestColor, false, ComponentId + TEXT(".arm")));
        // Retro-reflective vest bands remain visible at the wide operator camera.
        Attach(Shape(Cube, TorsoPosition + FVector(0, -14, 2), FVector(40, 4, 8),
            FLinearColor(.84, .88, .62), false, ComponentId + TEXT(".reflective"), .16f, .36f, .46f));
        if (bHardHat)
        {
            Attach(Shape(Cylinder, TorsoPosition + FVector(0, 0, 67), FVector(23, 23, 10),
                FLinearColor(.95, .73, .06), false, ComponentId + TEXT(".helmet"), .08f, .48f, .42f));
            Attach(Shape(Cube, TorsoPosition + FVector(0, -7, 62), FVector(52, 31, 4),
                FLinearColor(.95, .73, .06), false, ComponentId + TEXT(".helmet-brim"), .08f, .48f, .42f));
        }
        return Torso;
    };
    for (const auto& Entry : TArray<TPair<FString, FVector>>{
        TPair<FString, FVector>(TEXT("unloading"), FVector(-1750, -150, 105)), TPair<FString, FVector>(TEXT("compressor"), FVector(-640, -120, 105)),
        TPair<FString, FVector>(TEXT("storage"), FVector(300, -80, 105)), TPair<FString, FVector>(TEXT("dispenser"), FVector(420, 1020, 105))})
        PersonnelMeshes.Add(Entry.Key, AddPerson(Entry.Value, FLinearColor(.08, .34, .58),
            TEXT("personnel.") + Entry.Key, true));
    // A visitor and operator near the administration entrance give the idle
    // station a believable occupied scale while remaining outside process zones.
    AddPerson(FVector(-1190, 120, 105), FLinearColor(.82, .42, .06), TEXT("ambient.operator"), true);
    AddPerson(FVector(-1050, 110, 105), FLinearColor(.26, .33, .42), TEXT("ambient.visitor"), false);
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

void AHRSStationActor::ApplyCutaways()
{
    for (auto Mesh : CanopyCutawayMeshes) if (Mesh) Mesh->SetVisibility(!bRoofCutaway);
    for (auto Mesh : ServiceInteriorMeshes) if (Mesh) Mesh->SetVisibility(bServiceCutaway);
    SetImportedModelVisibility(TEXT("compressor"), !bServiceCutaway);
    SetImportedModelVisibility(TEXT("cooler"), !bServiceCutaway);
    for (auto Mesh : VehicleTankCutawayMeshes)
    {
        if (!Mesh || Mesh->ComponentTags.Num() == 0) continue;
        const bool bFirst = Mesh->ComponentTags[0].ToString() == TEXT("vehicle.tank");
        Mesh->SetVisibility(bVehicleCutaway && (bFirst ? bVehicle1Present : bVehicle2Present));
    }
    SetImportedModelVisibility(TEXT("vehicle.tank"), bVehicle1Present && !bVehicleCutaway);
    SetImportedModelVisibility(TEXT("vehicle_2.tank"), bVehicle2Present && !bVehicleCutaway);
}

void AHRSStationActor::ApplyViewState(const TSharedPtr<FJsonObject>& View)
{
    const bool NewRoof = Bool(View, TEXT("roof_cutaway"));
    const bool NewService = Bool(View, TEXT("service_cutaway"));
    const bool NewVehicle = Bool(View, TEXT("vehicle_cutaway"));
    const bool NewIncidents = Bool(View, TEXT("show_incidents"), true);
    const bool NewRisk = Bool(View, TEXT("show_risk"));
    const bool NewDistance = Bool(View, TEXT("show_distance"));
    const bool NewCameras = Bool(View, TEXT("show_cameras"));
    const bool NewDetectors = Bool(View, TEXT("show_detectors"));
    const bool bChanged = NewRoof != bRoofCutaway || NewService != bServiceCutaway ||
        NewVehicle != bVehicleCutaway || NewIncidents != bShowIncidents || NewRisk != bShowRisk ||
        NewDistance != bShowDistance || NewCameras != bShowCameras || NewDetectors != bShowDetectors;
    if (!bChanged) return;
    const bool bRiskStarted = NewRisk && !bShowRisk;
    bRoofCutaway = NewRoof; bServiceCutaway = NewService; bVehicleCutaway = NewVehicle;
    bShowIncidents = NewIncidents; bShowRisk = NewRisk; bShowDistance = NewDistance;
    bShowCameras = NewCameras; bShowDetectors = NewDetectors;
    ApplyCutaways();
    for (auto& Row : CameraMeshes) Row.Value->SetVisibility(bShowCameras, true);
    for (auto& Row : DetectorMeshes) Row.Value->SetVisibility(bShowDetectors, true);
    if (!bShowRisk) for (auto& Row : RiskMeshes) Row.Value->SetVisibility(false);
    if (!bShowDistance)
    {
        for (auto& Row : DistanceMeshes) Row.Value->SetVisibility(false);
        for (auto& Row : DistanceLabels) Row.Value->SetVisibility(false);
    }
    if (!bShowIncidents)
    {
        for (auto& Row : Jets) Row.Value->SetVisibility(false);
        for (auto& Row : HighlightMeshes) Row.Value->SetVisibility(false);
        for (auto& Row : FireMeshes) Row.Value->SetVisibility(false);
    }
    ++VisualRevision;
    if (!CurrentRun.IsEmpty())
    {
        if (bRiskStarted) RequestRisk();
        RequestSnapshot();
    }
}

void AHRSStationActor::BeginPlay()
{
    Super::BeginPlay();
    FParse::Value(FCommandLine::Get(), TEXT("HRSApi="), ApiBase);
    FParse::Value(FCommandLine::Get(), TEXT("HRSRenderer="), RendererId);
    ApiBase.RemoveFromEnd(TEXT("/"));
    OpaqueMaterial = LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/HRS/Materials/M_HRSOpaque.M_HRSOpaque"));
    PhysicalMaterial = LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/HRS/Materials/M_HRSPhysical.M_HRSPhysical"));
    TransparentMaterial = LoadObject<UMaterialInterface>(nullptr, TEXT("/Game/HRS/Materials/M_HRSTranslucent.M_HRSTranslucent"));
    BuildReferenceStation();
    BuildBank(TEXT("low"), FVector(-100, -600, 0), FLinearColor(.1, .48, .53));
    BuildBank(TEXT("medium"), FVector(300, -600, 0), FLinearColor(.52, .34, .13));
    BuildBank(TEXT("high"), FVector(700, -600, 0), FLinearColor(.32, .23, .56));
    SelectionMesh = Shape(Cube, Origins[Selected] + FVector(0, 0, Dimensions[Selected].Z * .5),
                          Dimensions[Selected] + FVector(55, 55, 55),
                          FLinearColor(.04, .42, .72), true);
    DiscoverImportedModels();
    StatusText = Text(FVector(300, 1180, 520), TEXT("Waiting for station session\n1/2/3 select | X inlet | Z outlet | E ESD | F stop\nR risk | D distance | C cameras | G detectors"), 22);
    GetWorldTimerManager().SetTimer(SessionTimer, this, &AHRSStationActor::PollBinding, 1.f, true, 0.f);
}

void AHRSStationActor::ResetVisualState()
{
    if (PendingFeedback) PendingFeedback->CancelRequest();
    PendingFeedback.Reset(); bFeedbackPending = false;
    LastSequence = -1; LastFeedbackSequence = -1; LastFeedbackVisualRevision = -1;
    LastSnapshotTicks = 0; LastReceive = 0; bTerminal = false;
    VisualRevision = 0; RecoveryCompleted = 0; RecoveryTotal = 0;
    AppliedValveStates.Empty(); AppliedAuxiliaryStates.Empty();
    bShowRisk = false; bShowDistance = false; bShowCameras = false; bShowDetectors = false;
    bRoofCutaway = false; bServiceCutaway = false; bVehicleCutaway = false; bShowIncidents = true;
    Selected = TEXT("cascade.high");
    for (auto& Row : Jets) { RemoveInstanceComponent(Row.Value); Row.Value->DestroyComponent(); }
    for (auto& Row : DistanceMeshes) { RemoveInstanceComponent(Row.Value); Row.Value->DestroyComponent(); }
    for (auto& Row : DistanceLabels) { RemoveInstanceComponent(Row.Value); Row.Value->DestroyComponent(); }
    Jets.Empty(); DistanceMeshes.Empty(); DistanceLabels.Empty();
    if (SelectionMesh)
    {
        SelectionMesh->SetRelativeLocation(Origins[Selected] + FVector(0, 0, Dimensions[Selected].Z * .5));
        SelectionMesh->SetRelativeScale3D((Dimensions[Selected] + FVector(55, 55, 55)) / 100.f);
        SelectionMesh->SetVisibility(true);
    }
    for (auto& Row : RiskMeshes) Row.Value->SetVisibility(false);
    for (auto& Row : HighlightMeshes) Row.Value->SetVisibility(false);
    for (auto& Row : FireMeshes) Row.Value->SetVisibility(false);
    for (auto& Row : CameraMeshes) Row.Value->SetVisibility(false, true);
    for (auto& Row : DetectorMeshes) { Row.Value->SetVisibility(false, true); Tint(Row.Value,
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
    ApplyCutaways();
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
        Self->ApplyViewState(Obj(Data, TEXT("view")));
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
    if (!Snapshot || bFeedbackPending || CurrentRun.IsEmpty() ||
        (LastSequence == LastFeedbackSequence && VisualRevision == LastFeedbackVisualRevision)) return;
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
    auto Visual = MakeShared<FJsonObject>();
    Visual->SetBoolField(TEXT("show_risk"), bShowRisk);
    Visual->SetBoolField(TEXT("show_distance"), bShowDistance);
    Visual->SetBoolField(TEXT("show_cameras"), bShowCameras);
    Visual->SetBoolField(TEXT("show_detectors"), bShowDetectors);
    Visual->SetBoolField(TEXT("roof_cutaway"), bRoofCutaway);
    Visual->SetBoolField(TEXT("service_cutaway"), bServiceCutaway);
    Visual->SetBoolField(TEXT("vehicle_cutaway"), bVehicleCutaway);
    Visual->SetBoolField(TEXT("show_incidents"), bShowIncidents);
    Visual->SetStringField(TEXT("risk_mode"), bRelativeRisk ? TEXT("relative") : TEXT("absolute"));
    Visual->SetStringField(TEXT("selected_equipment"), Selected);
    auto HoseMode = [](const TArray<TObjectPtr<UStaticMeshComponent>>& Parked,
                       const TArray<TObjectPtr<UStaticMeshComponent>>& Connected)
    {
        bool bParked = Parked.Num() > 0, bConnected = Connected.Num() > 0;
        for (const auto Part : Parked) bParked = bParked && Part && Part->IsVisible();
        for (const auto Part : Connected) bConnected = bConnected && Part && Part->IsVisible();
        return bParked && !bConnected ? TEXT("parked") :
               bConnected && !bParked ? TEXT("connected") : TEXT("invalid");
    };
    Visual->SetStringField(TEXT("hose_1_mode"), HoseMode(Hose1Parked, Hose1Connected));
    Visual->SetStringField(TEXT("hose_2_mode"), HoseMode(Hose2Parked, Hose2Connected));
    auto AddVisible = [Visual](const TCHAR* Key, const auto& Components)
    {
        TArray<FString> Keys;
        for (const auto& Row : Components) if (Row.Value && Row.Value->IsVisible()) Keys.Add(Row.Key);
        Keys.Sort();
        TArray<TSharedPtr<FJsonValue>> Values;
        for (const FString& Value : Keys) Values.Add(MakeShared<FJsonValueString>(Value));
        Visual->SetArrayField(Key, Values);
    };
    AddVisible(TEXT("visible_jets"), Jets);
    AddVisible(TEXT("visible_distances"), DistanceMeshes);
    AddVisible(TEXT("visible_distance_labels"), DistanceLabels);
    AddVisible(TEXT("visible_risk_components"), RiskMeshes);
    AddVisible(TEXT("visible_fire_components"), FireMeshes);
    AddVisible(TEXT("visible_highlight_components"), HighlightMeshes);
    AddVisible(TEXT("visible_cameras"), CameraMeshes);
    AddVisible(TEXT("visible_detectors"), DetectorMeshes);
    AddVisible(TEXT("visible_auxiliary"), AuxiliaryMeshes);
    TArray<TSharedPtr<FJsonValue>> Muster;
    TArray<FString> MusterZones;
    for (const auto& Row : PersonnelMeshes)
        if (Row.Value && Row.Value->IsVisible() && Row.Value->GetRelativeLocation().Y > 1000.f)
            MusterZones.Add(Row.Key);
    MusterZones.Sort();
    for (const FString& Zone : MusterZones) Muster.Add(MakeShared<FJsonValueString>(Zone));
    Visual->SetArrayField(TEXT("personnel_at_muster"), Muster);
    auto ValveState = MakeShared<FJsonObject>();
    for (const auto& Row : AppliedValveStates) ValveState->SetStringField(Row.Key, Row.Value);
    Visual->SetObjectField(TEXT("valve_states"), ValveState);
    auto AuxiliaryState = MakeShared<FJsonObject>();
    for (const auto& Row : AppliedAuxiliaryStates) AuxiliaryState->SetStringField(Row.Key, Row.Value);
    Visual->SetObjectField(TEXT("auxiliary_states"), AuxiliaryState);
    Visual->SetNumberField(TEXT("recovery_completed"), RecoveryCompleted);
    Visual->SetNumberField(TEXT("recovery_total"), RecoveryTotal);
    Payload->SetObjectField(TEXT("visual_state"), Visual);
    FString Body; FJsonSerializer::Serialize(Payload, TJsonWriterFactory<>::Create(&Body));
    const int64 AppliedSequence = LastSequence; const int32 AppliedVisualRevision = VisualRevision;
    const int32 Expected = Generation;
    bFeedbackPending = true; PendingFeedback = FHttpModule::Get().CreateRequest();
    PendingFeedback->SetURL(ApiBase + TEXT("/api/integrations/unreal/session/") + RendererId + TEXT("/feedback"));
    PendingFeedback->SetVerb(TEXT("POST")); PendingFeedback->SetHeader(TEXT("Content-Type"), TEXT("application/json"));
    PendingFeedback->SetTimeout(3.f); PendingFeedback->SetContentAsString(Body);
    TWeakObjectPtr<AHRSStationActor> Weak(this);
    PendingFeedback->OnProcessRequestComplete().BindLambda([Weak, Expected, AppliedSequence, AppliedVisualRevision](FHttpRequestPtr, FHttpResponsePtr Response, bool bSuccess) {
        if (!Weak.IsValid()) return;
        Weak->bFeedbackPending = false;
        if (Weak->Generation == Expected && bSuccess && Response.IsValid() && Response->GetResponseCode() == 200)
        {
            Weak->LastFeedbackSequence = AppliedSequence;
            Weak->LastFeedbackVisualRevision = AppliedVisualRevision;
        }
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
        {
            Tint(Mesh, Bool(State, TEXT("fault")) ? FLinearColor(.72, .04, .03) :
                 Bool(State, TEXT("running")) ? FLinearColor(.04, .55, .48) : FLinearColor(.35, .4, .42));
            AppliedAuxiliaryStates.Add(TEXT("fan.") + Zone,
                Bool(State, TEXT("fault")) ? TEXT("failed") : Bool(State, TEXT("running")) ? TEXT("running") : TEXT("stopped"));
        }
    }
    for (const FString Bank : {TEXT("low"), TEXT("medium"), TEXT("high")})
    {
        const auto State = Obj(Cooling, *Bank);
        UStaticMeshComponent* Mesh = AuxiliaryMeshes.FindRef(TEXT("cooling.") + Bank).Get();
        if (Mesh && State)
        {
            Tint(Mesh, Bool(State, TEXT("fault")) ? FLinearColor(.72, .04, .03) :
                 Bool(State, TEXT("running")) ? FLinearColor(.04, .38, .78) : FLinearColor(.35, .4, .42));
            AppliedAuxiliaryStates.Add(TEXT("cooling.") + Bank,
                Bool(State, TEXT("fault")) ? TEXT("failed") : Bool(State, TEXT("running")) ? TEXT("running") : TEXT("stopped"));
        }
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
        Marker->SetVisibility(Present > 0 || Safe > 0, true);
        if (Present > 0)
        {
            const FVector Position = Zone == TEXT("unloading") ? FVector(-1750, -150, 105) :
                Zone == TEXT("compressor") ? FVector(-640, -120, 105) :
                Zone == TEXT("storage") ? FVector(300, -80, 105) : FVector(420, 1020, 105);
            Marker->SetRelativeLocation(Position); Tint(Marker, FLinearColor(.15, .35, .58));
            AppliedAuxiliaryStates.Add(TEXT("personnel.") + Zone, TEXT("present"));
        }
        else if (Safe > 0)
        {
            Marker->SetRelativeLocation(FVector(-1850 + ZoneIndex * 85, 1060, 105));
            Tint(Marker, FLinearColor(.05, .55, .31));
            AppliedAuxiliaryStates.Add(TEXT("personnel.") + Zone, TEXT("evacuated"));
        }
        else AppliedAuxiliaryStates.Add(TEXT("personnel.") + Zone, TEXT("empty"));
        if (UStaticMeshComponent* Boundary = AuxiliaryMeshes.FindRef(TEXT("access.") + Zone).Get())
        {
            Boundary->SetVisibility(Bool(Restricted, *Zone));
            AppliedAuxiliaryStates.Add(TEXT("access.") + Zone,
                Bool(Restricted, *Zone) ? TEXT("restricted") : TEXT("released"));
        }
        if (UStaticMeshComponent* Power = AuxiliaryMeshes.FindRef(TEXT("power.") + Zone).Get())
        {
            Tint(Power, Bool(PowerIsolated, *Zone) ? FLinearColor(.12, .16, .18) : FLinearColor(.16, .55, .25));
            AppliedAuxiliaryStates.Add(TEXT("power.") + Zone,
                Bool(PowerIsolated, *Zone) ? TEXT("isolated") : TEXT("energized"));
        }
        ++ZoneIndex;
    }
    const auto Vehicles = Obj(Safety, TEXT("vehicles"));
    if (Vehicles)
    {
        const bool bVehicle1Visible = Num(Vehicles, TEXT("vehicle_1"), 1) > 0;
        const bool bVehicle2Visible = Num(Vehicles, TEXT("vehicle_2"), 1) > 0;
        const bool bTrailerVisible = Num(Vehicles, TEXT("trailer"), 1) > 0;
        bVehicle1Present = bVehicle1Visible; bVehicle2Present = bVehicle2Visible;
        if (UStaticMeshComponent* Vehicle = EquipmentMeshes.FindRef(TEXT("vehicle.tank")).Get())
            Vehicle->SetVisibility(!ImportedModelActors.Contains(TEXT("vehicle.tank")) && bVehicle1Visible && !bVehicleCutaway);
        SetImportedModelVisibility(TEXT("vehicle.tank"), bVehicle1Visible && !bVehicleCutaway);
        if (UStaticMeshComponent* Vehicle = EquipmentMeshes.FindRef(TEXT("vehicle_2.tank")).Get())
            Vehicle->SetVisibility(!ImportedModelActors.Contains(TEXT("vehicle_2.tank")) && bVehicle2Visible && !bVehicleCutaway);
        SetImportedModelVisibility(TEXT("vehicle_2.tank"), bVehicle2Visible && !bVehicleCutaway);
        if (UStaticMeshComponent* Trailer = EquipmentMeshes.FindRef(TEXT("supply")).Get())
            Trailer->SetVisibility(!ImportedModelActors.Contains(TEXT("supply")) && bTrailerVisible);
        SetImportedModelVisibility(TEXT("supply"), bTrailerVisible);
        ApplyCutaways();
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
        RecoveryCompleted = Completed; RecoveryTotal = Recovery->Values.Num();
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
            AppliedAuxiliaryStates.Add(TEXT("purge.") + Bank, bActive ? TEXT("running") : TEXT("inactive"));
            if (bActive)
            {
                const double Fraction = FMath::Clamp(Num(PurgeFractions, *Bank, 1.0), .005, 1.0);
                Purge->SetRelativeScale3D(FVector(.35, .35, FMath::Max(.25, Fraction) * 2.2));
            }
        }
        if (UStaticMeshComponent* Test = AuxiliaryMeshes.FindRef(TEXT("diagnostic.") + Bank).Get())
        {
            Test->SetVisibility(Diagnostic && DiagnosticBank == Bank);
            AppliedAuxiliaryStates.Add(TEXT("diagnostic.") + Bank,
                Diagnostic && DiagnosticBank == Bank ? Str(Diagnostic, TEXT("kind")) : TEXT("inactive"));
        }
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
    if (!bShowIncidents) return;
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
        AppliedValveStates.Add(Mesh.Key, !Valve ? TEXT("unknown") :
            Str(Valve, TEXT("status")) == TEXT("failed") ? TEXT("failed") :
            Str(Valve, TEXT("status")) == TEXT("moving") || Str(Valve, TEXT("status")) == TEXT("commanded") ? TEXT("moving") :
            Bool(Valve, TEXT("actual_open")) ? TEXT("open") : TEXT("closed"));
    }
    for (auto& Row : Jets) Row.Value->SetVisibility(false);
    for (auto& Row : DistanceMeshes) Row.Value->SetVisibility(false);
    for (auto& Row : DistanceLabels) Row.Value->SetVisibility(false);
    if (Snapshot->TryGetArrayField(TEXT("releases"), Rows)) for (const auto& Item : *Rows)
    {
        const auto Row = Item->AsObject(); if (!Row) continue;
        const FString Id = Str(Row, TEXT("component_id")), Release = Str(Row, TEXT("release_id"));
        const double Flow = Num(Row, TEXT("mass_flow_g_s"));
        if (!Origins.Contains(Id) || Flow <= 1.e-6 || Release.IsEmpty()) continue;
        const FVector Origin = Origins[Id] + FVector(0, 0, Num(Row, TEXT("outlet_height_m"), 1.5) * 100);
        const double Height = FMath::Clamp(60. + FMath::Sqrt(Flow) * 15., 60., 450.); // Schematic, not CFD.
        if (!Jets.Contains(Release)) Jets.Add(Release, Shape(Cone, Origin, FVector(42, 42, Height), FLinearColor(.65, .84, .88), true));
        Jets[Release]->SetRelativeLocation(Origin + FVector(0, 0, Height / 2));
        Jets[Release]->SetRelativeScale3D(FVector(.42, .42, Height / 100)); Jets[Release]->SetVisibility(bShowIncidents);
        const double Radius = FMath::Max(Num(Row, TEXT("sampled_effect_radius_m")), Num(Row, TEXT("flammable_plume_distance_m"))) * 100;
        if (Radius > 0)
        {
            if (!DistanceMeshes.Contains(Release)) DistanceMeshes.Add(Release,
                Shape(Cylinder, Origins[Id] + FVector(0, 0, 28), FVector(Radius * 2, Radius * 2, 3), FLinearColor(.85, .22, .08), true));
            DistanceMeshes[Release]->SetRelativeScale3D(FVector(Radius / 50, Radius / 50, .03));
            DistanceMeshes[Release]->SetVisibility(bShowDistance);
            if (!DistanceLabels.Contains(Release))
            {
                auto* Label = Text(Origins[Id] + FVector(Radius, 0, 95), TEXT(""), 24);
                Label->SetTextRenderColor(FColor(185, 48, 22));
                DistanceLabels.Add(Release, Label);
            }
            DistanceLabels[Release]->SetRelativeLocation(Origins[Id] + FVector(Radius, 0, 95));
            DistanceLabels[Release]->SetText(FText::FromString(
                FString::Printf(TEXT("Consequence distance %.1f m\nSchematic advisory"), Radius / 100.)));
            DistanceLabels[Release]->SetVisibility(bShowDistance);
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
    // A cold HyRAM-backed screening pass can take longer than 15 seconds on a
    // busy workstation.  This request runs asynchronously, so allow the
    // calculation to finish instead of silently leaving the floor overlay
    // empty after a transient timeout.
    Request->SetVerb(TEXT("GET")); Request->SetTimeout(30.f);
    TWeakObjectPtr<AHRSStationActor> Weak(this);
    Request->OnProcessRequestComplete().BindLambda([Weak, Expected](FHttpRequestPtr, FHttpResponsePtr Response, bool bSuccess) {
        if (Weak.IsValid() && Weak->Generation == Expected && bSuccess && Response.IsValid() && Response->GetResponseCode() == 200)
        {
            Weak->ApplyRisk(Parse(Response->GetContentAsString()));
            // Risk calculation is intentionally outside the high-rate snapshot path.
            // Ask for one cached snapshot after the result arrives so feedback records
            // the meshes that were actually made visible instead of the pre-result state.
            ++Weak->VisualRevision;
            Weak->RequestSnapshot();
        }
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

void AHRSStationActor::Select(const FString& Id)
{
    if (!Origins.Contains(Id) || !Dimensions.Contains(Id)) return;
    Selected = Id; ++VisualRevision;
    if (SelectionMesh)
    {
        SelectionMesh->SetRelativeLocation(Origins[Id] + FVector(0, 0, Dimensions[Id].Z * .5));
        SelectionMesh->SetRelativeScale3D((Dimensions[Id] + FVector(55, 55, 55)) / 100.f);
        SelectionMesh->SetVisibility(true);
    }
    RequestSnapshot();
}
void AHRSStationActor::CloseSelectedValve(bool bInlet)
{ FString Bank = Selected; Bank.RemoveFromStart(TEXT("cascade.")); IssueAction(TEXT("valve.close"), TEXT("bank.") + Bank + (bInlet ? TEXT(".inlet") : TEXT(".outlet"))); }
void AHRSStationActor::ToggleRisk() { bShowRisk = !bShowRisk; ++VisualRevision; if (!CurrentRun.IsEmpty()) { RequestRisk(); RequestSnapshot(); } }
void AHRSStationActor::ToggleDistance() { bShowDistance = !bShowDistance; ++VisualRevision; RequestSnapshot(); }
void AHRSStationActor::ToggleCameras()
{
    bShowCameras = !bShowCameras; ++VisualRevision;
    for (auto& Row : CameraMeshes) Row.Value->SetVisibility(bShowCameras, true);
    RequestSnapshot();
}
void AHRSStationActor::ToggleDetectors()
{
    bShowDetectors = !bShowDetectors; ++VisualRevision;
    for (auto& Row : DetectorMeshes) Row.Value->SetVisibility(bShowDetectors, true);
    RequestSnapshot();
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
        for (auto& Row : DistanceLabels) Row.Value->SetWorldRotation((Camera - Row.Value->GetComponentLocation()).Rotation());
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
