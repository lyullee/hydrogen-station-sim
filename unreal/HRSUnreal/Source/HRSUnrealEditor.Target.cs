using UnrealBuildTool;
using System.Collections.Generic;

public class HRSUnrealEditorTarget : TargetRules
{
    public HRSUnrealEditorTarget(TargetInfo Target) : base(Target)
    {
        Type = TargetType.Editor;
        DefaultBuildSettings = BuildSettingsVersion.V5;
        ExtraModuleNames.Add("HRSUnreal");
    }
}
