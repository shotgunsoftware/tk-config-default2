// UnrealWriter. Copyright 2020 Imaginary Spaces. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "UObject/NoExportTypes.h"
#include "MovieSceneSequence.h"
#include "Tracks/MovieSceneSubTrack.h"
#include "UnrealWriterPythonAPI.generated.h"

/**
 * 
 */
UCLASS()
class UNREALWRITER_API UUnrealWriterPythonAPI : public UObject
{
    GENERATED_BODY()

    UFUNCTION(BlueprintCallable, meta = (DisplayName = "Display Sequencer Actions Dialog", Keywords = "ImgSpc Sequencer Actions"), Category = "ImgSpc Unreal Writer")
    static bool DisplaySequencerActionsDialog(const FString &SequenceName = "");

    UFUNCTION(BlueprintCallable, meta = (DisplayName = "Is UnrealMenuItem Loaded", Keywords = "ImgSpc UnrealMenuItem"), Category = "ImgSpc Unreal Python")
    static bool IsUnrealMenuItemLoaded();

    UFUNCTION(BlueprintCallable, meta = (DisplayName = "Add Sequence On Row", Keywords = "ImgSpc Subscenes Sequence"), Category = "ImgSpc Sequencer Python")
    static void AddSequenceToSubtrack(UMovieSceneSubTrack *SubTrack, UMovieSceneSequence *Sequence);

    UFUNCTION(BlueprintCallable, meta = (DisplayName = "Open File Dialog", Keywords = "IDesktopPlatform::OpenFileDialog"), Category = "Desktop Platform")
    static TArray<FString> OpenFileDialog(
        const FString &DialogTitle,
        const FString &FileTypes);

    UFUNCTION(BlueprintCallable, meta = (DisplayName = "Sync Browser To Assets", Keywords = "ImgSpc Subscenes Sequence"), Category = "ImgSpc Sequencer Python")
    static void SyncBrowserToAssets(TArray<FString> AssetPaths);

    UFUNCTION(BlueprintCallable, meta = (DisplayName = "Create Sequence", Keywords = "Create Level Sequence"), Category = "Shot Browser Utility")
    void CreateSequence(const FString &ShotID, const TArray<FString> &Characters, const TMap<FString, FString> &TemplateKwargs);
};
