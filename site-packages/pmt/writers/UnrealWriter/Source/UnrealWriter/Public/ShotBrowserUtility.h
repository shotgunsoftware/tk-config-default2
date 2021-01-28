// UnrealWriter. Copyright 2020 Imaginary Spaces. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "UObject/NoExportTypes.h"
#include "ShotBrowserUtility.generated.h"

/**
 * 
 */
UCLASS(Blueprintable)
class UNREALWRITER_API UShotBrowserUtility : public UObject
{
	GENERATED_BODY()

public:
    UFUNCTION(BlueprintCallable, Category = Python)
        static UShotBrowserUtility* Get();

    UFUNCTION(BlueprintImplementableEvent, Category = Python)
        void CreateSequence(const FString &ShotID, const TArray<FString> &Characters, const TMap<FString, FString> &TemplateKwargs) const;
};
