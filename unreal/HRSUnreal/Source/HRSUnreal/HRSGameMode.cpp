#include "HRSGameMode.h"
#include "HRSStationActor.h"
#include "HRSCameraPawn.h"
#include "Engine/DirectionalLight.h"
#include "Engine/SkyLight.h"
#include "Components/SkyAtmosphereComponent.h"
#include "Engine/ExponentialHeightFog.h"
#include "Components/LightComponent.h"
#include "Components/SkyLightComponent.h"
#include "Components/DirectionalLightComponent.h"
#include "Components/ExponentialHeightFogComponent.h"
#include "Engine/World.h"

AHRSGameMode::AHRSGameMode() { DefaultPawnClass = AHRSCameraPawn::StaticClass(); }
void AHRSGameMode::BeginPlay()
{
    Super::BeginPlay();
    GetWorld()->SpawnActor<AHRSStationActor>();
    auto* Sun = GetWorld()->SpawnActor<ADirectionalLight>();
    Sun->SetActorRotation(FRotator(-42, -28, 0));
    Sun->GetLightComponent()->SetIntensity(7.5f);
    Sun->GetLightComponent()->SetLightColor(FLinearColor(1.f, .94f, .84f));
    if (auto* Directional = Cast<UDirectionalLightComponent>(Sun->GetLightComponent()))
    {
        Directional->SetAtmosphereSunLight(true);
        Directional->SetLightSourceAngle(.75f);
    }
    GetWorld()->SpawnActor<ASkyAtmosphere>();
    auto* Sky = GetWorld()->SpawnActor<ASkyLight>();
    Sky->GetLightComponent()->SetIntensity(.65f);
    Sky->GetLightComponent()->SetMobility(EComponentMobility::Movable);
    Sky->GetLightComponent()->RecaptureSky();
    auto* Fog = GetWorld()->SpawnActor<AExponentialHeightFog>();
    Fog->GetComponent()->SetFogDensity(.0022f);
    Fog->GetComponent()->SetFogHeightFalloff(.18f);
}
