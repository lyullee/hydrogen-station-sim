#pragma once
#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "HRSGameMode.generated.h"

UCLASS()
class HRSUNREAL_API AHRSGameMode : public AGameModeBase
{
    GENERATED_BODY()
public:
    AHRSGameMode();
    virtual void BeginPlay() override;
};
