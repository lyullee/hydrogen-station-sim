#include "HRSCameraPawn.h"
#include "HRSStationActor.h"
#include "Camera/CameraComponent.h"
#include "GameFramework/PlayerController.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Components/InputComponent.h"
#include "Components/PrimitiveComponent.h"
#include "InputCoreTypes.h"

AHRSCameraPawn::AHRSCameraPawn()
{
    PrimaryActorTick.bCanEverTick = true;
    Camera = CreateDefaultSubobject<UCameraComponent>(TEXT("Camera")); RootComponent = Camera;
    AutoPossessPlayer = EAutoReceiveInput::Player0;
}
void AHRSCameraPawn::BeginPlay()
{
    Super::BeginPlay();
    if (auto* PC = Cast<APlayerController>(GetController()))
    {
        PC->bShowMouseCursor = true;
        FInputModeGameAndUI InputMode;
        InputMode.SetHideCursorDuringCapture(false);
        InputMode.SetLockMouseToViewportBehavior(EMouseLockMode::DoNotLock);
        PC->SetInputMode(InputMode);
    }
}
AHRSStationActor* AHRSCameraPawn::Station() const
{ for (TActorIterator<AHRSStationActor> It(GetWorld()); It; ++It) return *It; return nullptr; }
void AHRSCameraPawn::Tick(float Dt)
{
    Super::Tick(Dt);
    if (auto* PC = Cast<APlayerController>(GetController()))
    {
        float DX, DY; PC->GetInputMouseDelta(DX, DY);
        if (PC->IsInputKeyDown(EKeys::MiddleMouseButton))
        {
            const FVector Right = Camera->GetRightVector();
            FVector Forward = Camera->GetForwardVector(); Forward.Z = 0; Forward.Normalize();
            Focus += (-Right * DX + Forward * DY) * Distance * .001f;
        }
        else if (PC->IsInputKeyDown(EKeys::LeftMouseButton))
        { Yaw -= DX * .3f; Pitch = FMath::Clamp(Pitch + DY * .3f, 8.f, 85.f); }
    }
    const FRotator Orbit(-Pitch, Yaw, 0);
    SetActorLocation(Focus - Orbit.Vector() * Distance); SetActorRotation(Orbit);
}
void AHRSCameraPawn::ZoomIn() { Distance = FMath::Clamp(Distance * .9f, 400.f, 6000.f); }
void AHRSCameraPawn::ZoomOut() { Distance = FMath::Clamp(Distance / .9f, 400.f, 6000.f); }
void AHRSCameraPawn::MousePressed()
{ if (auto* PC = Cast<APlayerController>(GetController())) PC->GetMousePosition(MouseDown.X, MouseDown.Y); }
void AHRSCameraPawn::Pick()
{
    auto* PC = Cast<APlayerController>(GetController()); if (!PC) return;
    FVector2D Now; PC->GetMousePosition(Now.X, Now.Y);
    if (FVector2D::Distance(Now, MouseDown) > 5) return;
    FHitResult Hit;
    if (PC->GetHitResultUnderCursor(ECC_Visibility, false, Hit) && Hit.GetComponent() &&
        Hit.GetComponent()->ComponentTags.Num() && Station())
        Station()->Select(Hit.GetComponent()->ComponentTags[0].ToString());
}
void AHRSCameraPawn::Low() { if (Station()) Station()->Select(TEXT("cascade.low")); }
void AHRSCameraPawn::Medium() { if (Station()) Station()->Select(TEXT("cascade.medium")); }
void AHRSCameraPawn::High() { if (Station()) Station()->Select(TEXT("cascade.high")); }
void AHRSCameraPawn::Inlet() { if (Station()) Station()->CloseSelectedValve(true); }
void AHRSCameraPawn::Outlet() { if (Station()) Station()->CloseSelectedValve(false); }
void AHRSCameraPawn::Esd() { if (Station()) Station()->IssueAction(TEXT("esd.trip"), TEXT("all")); }
void AHRSCameraPawn::Stop() { if (Station()) Station()->IssueAction(TEXT("operation.stop"), TEXT("all")); }
void AHRSCameraPawn::Risk() { if (Station()) Station()->ToggleRisk(); }
void AHRSCameraPawn::EffectDistance() { if (Station()) Station()->ToggleDistance(); }
void AHRSCameraPawn::SetupPlayerInputComponent(UInputComponent* Input)
{
    Super::SetupPlayerInputComponent(Input);
    Input->BindKey(EKeys::MouseScrollUp, IE_Pressed, this, &AHRSCameraPawn::ZoomIn);
    Input->BindKey(EKeys::MouseScrollDown, IE_Pressed, this, &AHRSCameraPawn::ZoomOut);
    Input->BindKey(EKeys::LeftMouseButton, IE_Pressed, this, &AHRSCameraPawn::MousePressed);
    Input->BindKey(EKeys::LeftMouseButton, IE_Released, this, &AHRSCameraPawn::Pick);
    Input->BindKey(EKeys::One, IE_Pressed, this, &AHRSCameraPawn::Low);
    Input->BindKey(EKeys::Two, IE_Pressed, this, &AHRSCameraPawn::Medium);
    Input->BindKey(EKeys::Three, IE_Pressed, this, &AHRSCameraPawn::High);
    Input->BindKey(EKeys::X, IE_Pressed, this, &AHRSCameraPawn::Inlet);
    Input->BindKey(EKeys::Z, IE_Pressed, this, &AHRSCameraPawn::Outlet);
    Input->BindKey(EKeys::E, IE_Pressed, this, &AHRSCameraPawn::Esd);
    Input->BindKey(EKeys::F, IE_Pressed, this, &AHRSCameraPawn::Stop);
    Input->BindKey(EKeys::R, IE_Pressed, this, &AHRSCameraPawn::Risk);
    Input->BindKey(EKeys::D, IE_Pressed, this, &AHRSCameraPawn::EffectDistance);
}
