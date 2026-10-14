#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Pawn.h"
#include "HRSCameraPawn.generated.h"
class UCameraComponent;
class AHRSStationActor;

UCLASS()
class HRSUNREAL_API AHRSCameraPawn : public APawn
{
    GENERATED_BODY()
public:
    AHRSCameraPawn();
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;
    virtual void SetupPlayerInputComponent(UInputComponent* Input) override;
private:
    UPROPERTY() TObjectPtr<UCameraComponent> Camera;
    FVector Focus = FVector(300, -600, 130);
    float Distance = 2400, Yaw = 55, Pitch = 38;
    FVector2D MouseDown;
    void ZoomIn(); void ZoomOut(); void Pick(); void MousePressed();
    void Low(); void Medium(); void High();
    void Inlet(); void Outlet(); void Esd(); void Stop(); void Risk(); void EffectDistance();
    AHRSStationActor* Station() const;
};
