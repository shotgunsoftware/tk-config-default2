// Copyright Epic Games, Inc. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "UObject/GCObject.h"
#include "EditorReimportHandler.h" 

#include "Kismet/BlueprintFunctionLibrary.h"
#include "EditorReimportManagerPythonAPIBPLibrary.generated.h"


// Expose to Python some methods to automate the reimporting of Assets
UCLASS()
class UEditorReimportHandlerPythonAPI : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()

	/**
	* Check if a given Asset can be reimported
	*
	* @param Obj - the Asset to check
	* @return true if given object can be reimported
	*/
	UFUNCTION(BlueprintCallable, Category = "Reimport Manager | Python API")
	static bool CanReimport(UObject* Obj);

	/**
	* Update an Asset's source files.
	*
	* @param Obj - the Asset to update
	* @param Filename - the new source file path
	* @param SourceFileIndex - index of the source file to update in the source files array
	*/
	UFUNCTION(BlueprintCallable, Category = "Reimport Manager | Python API")
	static void UpdateReimportPath(UObject* Obj, const FString& Filename, int32 SourceFileIndex);

	/**
	* Reimport the given object using one of its source files.
	*
	* @param Obj - the Asset to be reimported 
	* @param SourceFileIndex - index of the source file to reimport in the source files array
	* @return - true if the reimport was successful
	*/
	UFUNCTION(BlueprintCallable, Category = "Reimport Manager | Python API")
	static bool Reimport(UObject* Obj, int32 SourceFileIndex);
};
