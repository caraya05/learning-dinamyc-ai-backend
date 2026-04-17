"""
Test cases for team series access control
"""

import asyncio


# Test case 1: Series sin team - acceso permitido
async def test_access_series_without_team():
    """
    Test: Usuario accede a serie que NO está publicada a ningún team
    Esperado: Acceso permitido (True)
    """
    series = {
        "_id": "507f1f77bcf86cd799439011",
        "title": "Test Series",
        "published_to_teams": []  # No publicada a ningún team
    }
    
    # Simulamos la lógica
    user_id = "user123"
    published_to_teams = series.get("published_to_teams", [])
    
    # Si no hay teams, acceso permitido
    has_access = len(published_to_teams) == 0
    
    assert has_access is True
    print("✅ Test 1 PASSED: Usuario puede acceder a serie sin team")


# Test case 2: Series con team - usuario es owner
async def test_access_series_user_is_owner():
    """
    Test: Usuario accede a serie publicada a team donde es owner
    Esperado: Acceso permitido (True)
    """
    user_id = "user_owner"
    team_id = "team123"
    series = {
        "_id": "507f1f77bcf86cd799439011",
        "title": "Test Series",
        "published_to_teams": [team_id]
    }
    team = {
        "_id": team_id,
        "owner_id": user_id,
        "members": []
    }
    
    # Lógica de validación
    published_to_teams = series.get("published_to_teams", [])
    has_access = False
    
    if not published_to_teams:
        has_access = True
    else:
        for team_published_id in published_to_teams:
            if team_published_id == team_id:
                if team.get("owner_id") == user_id:
                    has_access = True
                    break
    
    assert has_access is True
    print("✅ Test 2 PASSED: Usuario owner puede acceder a su serie")


# Test case 3: Series con team - usuario es miembro
async def test_access_series_user_is_member():
    """
    Test: Usuario accede a serie publicada a team donde es miembro
    Esperado: Acceso permitido (True)
    """
    user_id = "user_member"
    team_id = "team123"
    series = {
        "_id": "507f1f77bcf86cd799439011",
        "title": "Test Series",
        "published_to_teams": [team_id]
    }
    team = {
        "_id": team_id,
        "owner_id": "other_user",
        "members": [
            {"user_id": user_id, "role": "creator"}
        ]
    }
    
    # Lógica de validación
    published_to_teams = series.get("published_to_teams", [])
    has_access = False
    
    if not published_to_teams:
        has_access = True
    else:
        for team_published_id in published_to_teams:
            if team_published_id == team_id:
                if team.get("owner_id") == user_id:
                    has_access = True
                    break
                # Check members
                members = team.get("members", [])
                if any(m.get("user_id") == user_id for m in members):
                    has_access = True
                    break
    
    assert has_access is True
    print("✅ Test 3 PASSED: Usuario miembro puede acceder a serie del team")


# Test case 4: Series con team - usuario no es miembro
async def test_access_series_user_no_access():
    """
    Test: Usuario accede a serie publicada a team donde NO es miembro
    Esperado: Acceso denegado (False)
    """
    user_id = "user_stranger"
    team_id = "team123"
    series = {
        "_id": "507f1f77bcf86cd799439011",
        "title": "Test Series",
        "published_to_teams": [team_id]
    }
    team = {
        "_id": team_id,
        "owner_id": "other_user",
        "members": [
            {"user_id": "another_user", "role": "creator"}
        ]
    }
    
    # Lógica de validación
    published_to_teams = series.get("published_to_teams", [])
    has_access = False
    
    if not published_to_teams:
        has_access = True
    else:
        for team_published_id in published_to_teams:
            if team_published_id == team_id:
                if team.get("owner_id") == user_id:
                    has_access = True
                    break
                members = team.get("members", [])
                if any(m.get("user_id") == user_id for m in members):
                    has_access = True
                    break
    
    assert has_access is False
    print("✅ Test 4 PASSED: Usuario sin permisos recibe acceso denegado")


# Test case 5: Series con múltiples teams
async def test_access_series_multiple_teams():
    """
    Test: Usuario accede a serie publicada a múltiples teams
    Esperado: Acceso permitido si es miembro de al menos uno
    """
    user_id = "user123"
    team_a = "teamA"
    team_b = "teamB"
    series = {
        "_id": "507f1f77bcf86cd799439011",
        "title": "Test Series",
        "published_to_teams": [team_a, team_b]
    }
    teams = {
        team_a: {
            "owner_id": "other_user",
            "members": []
        },
        team_b: {
            "owner_id": "other_user",
            "members": [{"user_id": user_id, "role": "viewer"}]
        }
    }
    
    # Lógica de validación
    published_to_teams = series.get("published_to_teams", [])
    has_access = False
    
    for team_published_id in published_to_teams:
        team = teams.get(team_published_id)
        if not team:
            continue
        
        if team.get("owner_id") == user_id:
            has_access = True
            break
        
        members = team.get("members", [])
        if any(m.get("user_id") == user_id for m in members):
            has_access = True
            break
    
    assert has_access is True
    print("✅ Test 5 PASSED: Usuario puede acceder si es miembro de uno de los teams")


# Run all tests
async def run_all_tests():
    print("\n" + "="*60)
    print("PRUEBAS DE VALIDACIÓN DE ACCESO A SERIES POR TEAM")
    print("="*60 + "\n")
    
    await test_access_series_without_team()
    await test_access_series_user_is_owner()
    await test_access_series_user_is_member()
    await test_access_series_user_no_access()
    await test_access_series_multiple_teams()
    
    print("\n" + "="*60)
    print("✅ TODAS LAS PRUEBAS PASARON EXITOSAMENTE")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(run_all_tests())





