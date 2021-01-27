// UnrealWriter. Copyright 2020 Imaginary Spaces. All Rights Reserved.


#include "ShotBrowserUtility.h"

UShotBrowserUtility* UShotBrowserUtility::Get()
{
    TArray<UClass*> ShotBrowserUtilityClasses;
    GetDerivedClasses(UShotBrowserUtility::StaticClass(), ShotBrowserUtilityClasses);
    int32 NumClasses = ShotBrowserUtilityClasses.Num();
    if (NumClasses > 0)
    {
        return Cast<UShotBrowserUtility>(ShotBrowserUtilityClasses[NumClasses - 1]->GetDefaultObject());
    }
    return nullptr;
}