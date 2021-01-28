// UnrealWriter. Copyright 2020 Imaginary Spaces. All Rights Reserved.

#include "UnrealWriterPythonAPI.h"
#include "ShotBrowserUtility.h"

#include "Misc/MessageDialog.h"
#include "MovieSceneTimeHelpers.h"

#include "IDesktopPlatform.h"
#include "DesktopPlatformModule.h"

#include "Editor/ContentBrowser/Public/ContentBrowserModule.h"
#include "Editor/ContentBrowser/Private/SContentBrowser.h"
#include "Runtime/AssetRegistry/Public/AssetRegistryModule.h"

const FName UnrealMenuItem_ModuleName = "UnrealMenuItem";

bool UUnrealWriterPythonAPI::DisplaySequencerActionsDialog(const FString &SequenceName)
{
    const FText MessageTitle = FText::FromString("UnrealWriter Sequence Assembly");
    const FText Message = FText::Format(FText::FromString("The following actions will be executed to assemble the Unreal sequence: {0}"), FText::FromString(SequenceName));

    EAppReturnType::Type Response = FMessageDialog::Open(EAppMsgType::OkCancel, Message, &MessageTitle);
    return Response == EAppReturnType::Ok;
}

bool UUnrealWriterPythonAPI::IsUnrealMenuItemLoaded()
{
    FModuleManager &ModuleManager = FModuleManager::Get();
    return ModuleManager.IsModuleLoaded(UnrealMenuItem_ModuleName);
}

void UUnrealWriterPythonAPI::AddSequenceToSubtrack(UMovieSceneSubTrack *SubTrack, UMovieSceneSequence *Sequence)
{
    const FFrameRate TickResolution = Sequence->GetMovieScene()->GetTickResolution();

#if ENGINE_MINOR_VERSION > 25
    const FFrameTime SequenceRange = UE::MovieScene::DiscreteSize(Sequence->GetMovieScene()->GetPlaybackRange());
#else
    const FFrameTime SequenceRange = MovieScene::DiscreteSize(Sequence->GetMovieScene()->GetPlaybackRange());
#endif

    const FQualifiedFrameTime InnerDuration = FQualifiedFrameTime(SequenceRange, TickResolution);

    const FFrameRate OuterFrameRate = SubTrack->GetTypedOuter<UMovieScene>()->GetTickResolution();
    const int32 OuterDuration = InnerDuration.ConvertTo(OuterFrameRate).FrameNumber.Value;

    SubTrack->AddSequenceOnRow(Sequence, FFrameNumber(0), OuterDuration, INDEX_NONE);
}

TArray<FString> UUnrealWriterPythonAPI::OpenFileDialog(
    const FString &DialogTitle,
    const FString &FileTypes)
{
    TArray<FString> outFileNames;

    IDesktopPlatform *desktopPlatform = FDesktopPlatformModule::Get();
    if (desktopPlatform)
    {
        desktopPlatform->OpenFileDialog(
            NULL,        // ParentWindowHandle
            DialogTitle, // DialogTitle
            "",          // DefaultPath
            "",          // DefaultFile,
            FileTypes,   // FileTypes,
            0,           // Flags,
            outFileNames);
    }
    return outFileNames;
}

void UUnrealWriterPythonAPI::SyncBrowserToAssets(TArray<FString> Paths)
{
    FContentBrowserModule &ContentBrowserModule = FModuleManager::LoadModuleChecked<FContentBrowserModule>("ContentBrowser");
    FAssetRegistryModule &AssetRegistryModule = FModuleManager::LoadModuleChecked<FAssetRegistryModule>("AssetRegistry");
    TArray<FName> pathNames;
    for (FString path : Paths)
    {
        pathNames.Add(*path);
    }
    FARFilter AssetFilter;
    AssetFilter.PackageNames = pathNames;
    TArray<FAssetData> assetData;
    AssetRegistryModule.Get().GetAssets(AssetFilter, assetData);
    ContentBrowserModule.Get().SyncBrowserToAssets(assetData);
}

void UUnrealWriterPythonAPI::CreateSequence(const FString &ShotID, const TArray<FString> &Characters, const TMap<FString, FString> &TemplateKwargs)
{
    UShotBrowserUtility* bridge = UShotBrowserUtility::Get();
    bridge->CreateSequence(ShotID, Characters, TemplateKwargs);
}
