#include "HRSGameMode.h"
#include "HRSStationActor.h"
#include "HRSCameraPawn.h"
#include "Engine/DirectionalLight.h"
#include "Engine/SkyLight.h"
#include "Components/LightComponent.h"
#include "Components/SkyLightComponent.h"
#include "Engine/World.h"

AHRSGameMode::AHRSGameMode() { DefaultPawnClass = AHRSCameraPawn::StaticClass(); }
void AHRSGameMode::BeginPlay()
{
    Super::BeginPlay();
    GetWorld()->SpawnActor<AHRSStationActor>();
    auto* Sun = GetWorld()->SpawnActor<ADirectionalLight>();
    Sun->SetActorRotation(FRotator(-50, -30, 0));
    Sun->GetLightComponent()->SetIntensity(2.f);
    auto* Sky = GetWorld()->SpawnActor<ASkyLight>();
    Sky->GetLightComponent()->SetIntensity(.8f);
    Sky->GetLightComponent()->SetMobility(EComponentMobility::Movable);
    Sky->GetLightComponent()->RecaptureSky();
}
