#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Interfaces/IHttpRequest.h"
#include "Dom/JsonObject.h"
#include "HRSStationActor.generated.h"

class UStaticMeshComponent;
class UTextRenderComponent;
class UMaterialInterface;
class IWebSocket;

UCLASS()
class HRSUNREAL_API AHRSStationActor : public AActor
{
    GENERATED_BODY()
public:
    AHRSStationActor();
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    void Select(const FString& ComponentId);
    void IssueAction(const FString& Kind, const FString& Target);
    void CloseSelectedValve(bool bInlet);
    void ToggleRisk();
    void ToggleDistance();
    void ToggleCameras();
    void ToggleDetectors();

private:
    UPROPERTY() TObjectPtr<USceneComponent> SceneRoot;
    UPROPERTY() TObjectPtr<UMaterialInterface> OpaqueMaterial;
    UPROPERTY() TObjectPtr<UMaterialInterface> TransparentMaterial;
    UPROPERTY() TObjectPtr<UTextRenderComponent> StatusText;
    UPROPERTY() TMap<FString, TObjectPtr<UTextRenderComponent>> Labels;
    UPROPERTY() TMap<FString, TObjectPtr<UStaticMeshComponent>> ValveMeshes;
    UPROPERTY() TMap<FString, TObjectPtr<UStaticMeshComponent>> Jets;
    UPROPERTY() TMap<FString, TObjectPtr<UStaticMeshComponent>> DistanceMeshes;
    UPROPERTY() TMap<FString, TObjectPtr<UStaticMeshComponent>> RiskMeshes;
    UPROPERTY() TMap<FString, TObjectPtr<UStaticMeshComponent>> EquipmentMeshes;
    UPROPERTY() TMap<FString, TObjectPtr<UStaticMeshComponent>> HighlightMeshes;
    UPROPERTY() TMap<FString, TObjectPtr<UStaticMeshComponent>> FireMeshes;
    UPROPERTY() TMap<FString, TObjectPtr<UStaticMeshComponent>> DetectorMeshes;
    UPROPERTY() TMap<FString, TObjectPtr<UStaticMeshComponent>> CameraMeshes;
    UPROPERTY() TMap<FString, TObjectPtr<UStaticMeshComponent>> AuxiliaryMeshes;
    UPROPERTY() TMap<FString, TObjectPtr<UStaticMeshComponent>> PersonnelMeshes;
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> Hose1Parked;
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> Hose1Connected;
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> Hose2Parked;
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> Hose2Connected;
    TMap<FString, FVector> Origins;
    TMap<FString, FVector> Dimensions;
    TMap<FString, FString> Names;
    FString ApiBase = TEXT("http://127.0.0.1:8000");
    FString RendererId = TEXT("default");
    FString CurrentRun;
    FString Selected = TEXT("cascade.high");
    int32 Generation = -1;
    int64 LastSequence = -1;
    int64 LastFeedbackSequence = -1;
    int64 LastSnapshotTicks = 0;
    int32 ConnectionSerial = 0;
    bool bBindingPending = false;
    bool bSnapshotPending = false;
    bool bFeedbackPending = false;
    bool bConnecting = false;
    bool bTerminal = false;
    bool bShowRisk = false;
    bool bShowDistance = false;
    bool bShowCameras = false;
    bool bShowDetectors = false;
    bool bRelativeRisk = true;
    double LastReceive = 0;
    double NextRetry = 0;
    double RetryDelay = 1;
    double LastRiskRequest = -100;
    TSharedPtr<IWebSocket> Socket;
    TSharedPtr<IHttpRequest, ESPMode::ThreadSafe> PendingBinding;
    TSharedPtr<IHttpRequest, ESPMode::ThreadSafe> PendingSnapshot;
    TSharedPtr<IHttpRequest, ESPMode::ThreadSafe> PendingFeedback;
    FTimerHandle SessionTimer;
    void PollBinding();
    void ConnectStream();
    void RequestSnapshot();
    void RequestRisk();
    void SendFeedback(const TSharedPtr<FJsonObject>& Snapshot);
    void ResetVisualState();
    void ApplySnapshot(const TSharedPtr<FJsonObject>& Snapshot);
    void ApplyRisk(const TSharedPtr<FJsonObject>& Risk);
    void ApplyAuxiliaryState(const TSharedPtr<FJsonObject>& Safety);
    void ApplyProcessState(const TSharedPtr<FJsonObject>& Snapshot);
    void ApplyIncidentState(const TSharedPtr<FJsonObject>& Snapshot);
    void BuildReferenceStation();
    void BuildBank(const FString& Bank, const FVector& Origin, const FLinearColor& Color);
    void BuildHose(TArray<TObjectPtr<UStaticMeshComponent>>& Parts,
        const TArray<FVector>& Points, const FString& ComponentId);
    UStaticMeshComponent* Shape(const TCHAR* MeshPath, const FVector& Position,
        const FVector& Size, const FLinearColor& Color, bool bTransparent = false,
        const FString& ComponentId = FString());
    UStaticMeshComponent* Segment(const FVector& Start, const FVector& End,
        float Diameter, const FLinearColor& Color, bool bTransparent = false,
        const FString& ComponentId = FString());
    UTextRenderComponent* Text(const FVector& Position, const FString& Value, float Size = 22);
    void Tint(UStaticMeshComponent* Mesh, const FLinearColor& Color);
};
