using UnrealBuildTool;

public class HRSUnreal : ModuleRules
{
    public HRSUnreal(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
        PublicDependencyModuleNames.AddRange(new[] {
            "Core", "CoreUObject", "Engine", "InputCore", "HTTP", "Json", "WebSockets"
        });
    }
}
